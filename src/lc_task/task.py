from __future__ import annotations

import dataclasses
import logging
import sys
import typing
from argparse import Namespace

__author__ = "libcommon"
logger = logging.getLogger(__name__)
_TTask = typing.TypeVar("_TTask", bound="Task")  # pylint: disable=invalid-name
#: Types that can be merged into :class:`.Task` (see :meth:`.Task.merge_object`).
StatePropagationSource = typing.Union[
    typing.Dict[str, typing.Any],
    typing.Optional["TaskResult"],
    Namespace,
    "Task",
]


def _gen_pairs_from_slots_object(
    obj: typing.Union["Task", "TaskResult"]
) -> typing.Tuple[typing.Tuple[str, typing.Any], ...]:
    """Generate tuple of attribute name-value pairs from object that defines
    the __slots__ variable.
    Raises:
        TypeError: if obj doesn't define __slots__
    """
    if not hasattr(obj, "__slots__"):
        raise TypeError(f"{type(obj).__name__} does not define __slots__")
    return tuple(
        (attr_name, getattr(obj, attr_name))
        for attr_name in dir(obj)
        if not attr_name.startswith("_") and not callable(getattr(obj, attr_name))
    )


def _gen_pairs_from_object(
    obj: StatePropagationSource,
) -> typing.Union[typing.Tuple[()], typing.Tuple[typing.Tuple[str, typing.Any], ...]]:
    """Generate tuple of attribute name-value pairs from supported types.

    Raises:
        TypeError: If obj is not a supported type
    """
    if obj is None:
        items: typing.Union[typing.Tuple[()], typing.Tuple[typing.Tuple[str, typing.Any], ...]] = tuple()
    elif isinstance(obj, dict):
        items = tuple(obj.items())
    elif isinstance(obj, Namespace):
        items = tuple(obj._get_kwargs())
    # isinstance(obj, (Task, TaskResult))
    else:
        items = _gen_pairs_from_slots_object(obj)
    return items


# The ``dataclasses.dataclass`` decorator in Python <=3.9 does not support the ``slots`` argument.
# For those versions, we backport the code from Python 3.10, where the ``slots`` feature was added.
# TODO: Remove When this library drops support for Python 3.9.
if sys.version_info < (3, 10):
    # _dataclass_getstate and _dataclass_setstate are needed for pickling frozen classes with slots.
    # These could be slighly more performant if we generated the code instead of iterating over fields.
    # But that can be a project for another day, if performance becomes an issue.
    def _dataclass_getstate(self) -> typing.List[typing.Any]:
        return [getattr(self, f.name) for f in dataclasses.fields(self)]

    def _dataclass_setstate(self, state: typing.List[typing.Any]) -> None:
        for field, value in zip(dataclasses.fields(self), state):
            # use setattr because dataclass may be frozen
            object.__setattr__(self, field.name, value)

    def _add_slots(cls, is_frozen: bool):
        if "__slots__" in cls.__dict__:
            raise TypeError(f"{cls.__name__} already specifies __slots__")

        # Create a new dict for our new class.
        cls_dict = dict(cls.__dict__)
        field_names = tuple(f.name for f in dataclasses.fields(cls))
        # Set __slots__ on new class to dataclass fields
        cls_dict["__slots__"] = field_names
        # Remove our attributes, if present - they'll still be available in _MARKER
        for field_name in field_names:
            cls_dict.pop(field_name, None)

        # Remove __dict__ itself, slotted classes don't have __dict__
        cls_dict.pop("__dict__", None)

        # And finally create the class.
        qualname = getattr(cls, "__qualname__", None)
        cls = type(cls)(cls.__name__, cls.__bases__, cls_dict)
        if qualname is not None:
            cls.__qualname__ = qualname

        if is_frozen:
            # Need this for pickling frozen classes with slots.
            cls.__getstate__ = _dataclass_getstate
            cls.__setstate__ = _dataclass_setstate

        return cls

    def _taskclass_wrap(cls, **kwargs):
        add_slots = kwargs.pop("slots", False)
        cls = dataclasses.dataclass(cls, **kwargs)
        if add_slots:
            cls = _add_slots(cls, kwargs.get("frozen", False))
        return cls

else:

    def _taskclass_wrap(cls, **kwargs):
        return dataclasses.dataclass(cls, **kwargs)


def taskclass(cls, **kwargs):
    """Task class decorator.

    All :class:`.TaskResult` and :class:`.Task` classes are :mod:`dataclasses` with the same options set.
    This convenience decorator sets those options by default, which include:

    * ``eq=True``
    * ``slots=True``

    All options supported by that :func:`dataclasses.dataclass` are supported, with one caveat.
    The ``slots`` feature is only supported in :mod:`dataclasses` in Python >=3.10,
    but it's supported in all Python versions supported by this library.

    Examples:

    Create a :class:`.TaskResult` child class:

    >>> import dataclasses
    >>> import sys
    >>> from lc_task import TaskResult, taskclass
    >>> # Using taskclass
    >>> @taskclass
    ... class SomeTaskResult(TaskResult):
    ...     some_result: typing.Optional[str] = None
    >>> assert hasattr(SomeTaskResult, "__slots__")
    >>> # Using dataclass
    >>> # The ``slots`` feature in dataclasses is only available in Python >=3.10,
    >>> # but is available in taskclass in all supported Python versions
    >>> if sys.version_info.major == 3 and sys.version_info.minor >= 10:
    ...     @dataclasses.dataclass(eq=True, slots=True)
    ...     class SomeOtherTaskResult(TaskResult):
    ...         some_result: typing.Optional[str] = None
    ...     # Both classes define __slots__ with the field some_result
    ...     assert SomeTaskResult.__slots__ == SomeOtherTaskResult.__slots__
    ... else:
    ...     @dataclasses.dataclass(eq=True)
    ...     class SomeOtherTaskResult(TaskResult):
    ...         some_result: typing.Optional[str] = None
    >>> # Both classes define an __eq__ method
    >>> assert hasattr(SomeTaskResult, "__eq__")
    >>> assert hasattr(SomeOtherTaskResult, "__eq__")
    """
    kwargs.setdefault("eq", True)
    kwargs.setdefault("slots", True)

    def wrap(cls):
        return _taskclass_wrap(cls, **kwargs)

    # cls is ``None`` if called as taskclass(**kwargs)
    return wrap if cls is None else wrap(cls)


@taskclass
class TaskResult:
    """Result of running a task.

    Use to pass result data to other compatible tasks.
    By default, the Exception raised from running the task (if occurred) is passed.
    Fields should be :data:`typing.Optional` so :class:`.Task` can instantiate the result class without parameters
    (via :attr:`.Task._result_cls`).
    """

    #: Exception raised during task execution, if any.
    #: Will be ``None`` if no exceptionn raised for :attr:`.Task.raise_exceptions` is ``True``.
    err: typing.Optional[Exception] = None


@taskclass
class Task:
    """Base task.

    Cannot be used directly. Child classes must implement :meth:`.Task._perform_task`.

    Examples:

    Create a task to count the number of lines in a file:

    >>> import tempfile
    >>> from pathlib import Path
    >>> from lc_task import Task, TaskResult, taskclass
    >>> @taskclass
    ... class CountLinesTaskResult(TaskResult):
    ...     num_lines: int = 0
    ...
    >>> @taskclass
    ... class CountLinesTask(Task):
    ...     _result_cls = CountLinesTaskResult
    ...     input_path: typing.Optional[str] = None
    ...     def _perform_task(self) -> None:
    ...         input_path: Path = Path(self.input_path or "")
    ...         if not input_path.is_file():
    ...             raise FileNotFoundError(self.input_path)
    ...         num_lines = 0
    ...         with input_path.open() as input_file:
    ...             for _ in input_file:
    ...                 num_lines += 1
    ...         self.result.num_lines = num_lines
    ...
    >>> with tempfile.NamedTemporaryFile() as tmp_file:
    ...     # Write ten lines to file
    ...     for _ in range(10):
    ...         __ = tmp_file.write(b"\\n")
    ...     # Flush writes
    ...     tmp_file.flush()
    ...     result = CountLinesTask(input_path=tmp_file.name).run()
    ...     assert result.num_lines == 10
    """

    #: Attributes to exclude from merge in :meth:`.Task.merge_object`.
    _exclude_from_merge: typing.ClassVar[typing.Set[str]] = set()
    #: Type of result from running the task (see: :attr:`.Task.result`).
    _result_cls: typing.ClassVar[typing.Type[TaskResult]] = TaskResult

    #: Raise any exceptions in :meth:`.Task._perform_task` instead of capturing them in the task result.
    raise_exceptions: bool = False
    #: Result from running the task.
    result: TaskResult = dataclasses.field(init=False)

    def __post_init__(self) -> None:
        self.result = self._result_cls()
        # These are always excluded from merge
        self._exclude_from_merge.update({"raise_exceptions", "result"})

    def _postamble(self) -> None:
        """Perform cleanup steps after task is completed.

        Should *not* raise an exception, as this method always runs even if task fails.
        """

    def _perform_task(self) -> None:
        """Perform the task.

        Child classes should set attributes on :attr:`.Task.result` in this function.
        """

    def _preamble(self) -> None:
        """Perform setup steps before running the task.

        Should *not* raise an exception, as this method always runs even if task fails.
        """

    def run(self) -> TaskResult:
        """Run the task.

        Returns:
            The task result (as defined on :attr:`.Task._result_cls`).

        Raises:
            Exception: Any exceptions raised in :meth:`.Task._perform_task` if :attr:`.Task.raise_exceptions`.
        """
        task_type = type(self).__name__
        logger.info("Running task %s", task_type)

        self._preamble()

        try:
            self._perform_task()
            logger.info("Finished running task %s", task_type)
        except Exception as exc:
            # Set exception on result before re-raising for use in _postamble()
            self.result.err = exc
            if self.raise_exceptions:
                raise
            logger.error("Failed to run task %s (%s)", task_type, exc)
        finally:
            self._postamble()

        return self.result

    def merge_object(
        self: _TTask,
        obj: StatePropagationSource,
        include: typing.Optional[typing.Set[str]] = None,
        exclude: typing.Optional[typing.Set[str]] = None,
        overwrite: typing.Optional[typing.Dict[str, typing.Any]] = None,
    ) -> _TTask:
        """Merge object into this task.

        Only attributes defined on the class are merged.
        ``include`` and ``exclude`` can be used to further control merge behavior.
        If both ``include`` and ``exclude`` are specified, ``exclude`` takes priority and ``include`` is ignored.
        For :class:`.Namespace`, all ``kwargs`` are merged.
        For :class:`.Task` and :class:`.TaskResult`, all variables in ``__slots__`` are merged.

        Args:
            obj: object to merge.
            include: attributes/values to merge.
            exclude: attributes/values not to merge.
            overwrite: overwrite values after merging the object.

        Returns:
            ``self``.
        """
        # Generate items iterable based on type of obj
        items = _gen_pairs_from_object(obj)
        # typing.Set whether exclude and include given
        exclude_given = bool(exclude)
        include_given = bool(include)
        # If exclude is defined, takes precedence over include
        if exclude_given and include_given:
            include = None
            include_given = False
        exclude = (exclude or set()) | self._exclude_from_merge
        if bool(exclude):
            exclude_given = True
        exclude_include_given = exclude_given or include_given
        # For each name-value pair in items
        for name, value in items:
            # Merge name-value pair if:
            #   1) Name is a valid attribute
            #   2) Neither exclude nor include (nor _exclude_from_merge) are set
            #   3) Name isn't in exclude, _and_
            #     a. include isn't provided
            #     b. name is in include
            if hasattr(self, name) and (
                not exclude_include_given
                or (name not in exclude and (not include_given or name in include))  # type: ignore
            ):
                setattr(self, name, value)
        if overwrite is not None:
            for name, value in overwrite.items():
                if hasattr(self, name):
                    setattr(self, name, value)
        return self

    def __ror__(self, task_result: TaskResult) -> TaskResult:
        """Merge result from previous task and run this one.

        Overloads the ``|`` operator to enable writing pipelines of tasks like the following:

        .. code-block:: python

            (Task1().run() | Task2() | Task3())

        Where the result from each task will propagate through the pipeline to the next task.
        This requires that the ``__or__`` function is not defined on any tasks,
        as Python will then not call the ``__ror__`` function.

        Args:
            task_result: result from the previous task.

        Returns:
            Result from running this task (see: :meth:`.Task.run`).
        """
        self.merge_object(task_result)
        return self.run()
