## -*- coding: UTF-8 -*-
## task.py
##
## Copyright (c) 2019 libcommon
##
## Permission is hereby granted, free of charge, to any person obtaining a copy
## of this software and associated documentation files (the "Software"), to deal
## in the Software without restriction, including without limitation the rights
## to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
## copies of the Software, and to permit persons to whom the Software is
## furnished to do so, subject to the following conditions:
##
## The above copyright notice and this permission notice shall be included in all
## copies or substantial portions of the Software.
##
## THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
## IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
## FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
## AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
## LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
## OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
## SOFTWARE.


from argparse import Namespace
import logging
import os
from typing import Any, ClassVar, Dict, Optional, Set, Tuple, TypeVar, Union


__author__ = "libcommon"
logger = logging.getLogger(__name__)    # pylint: disable=C0103
StatePropogationSource = TypeVar("StatePropogationSource",
                                 Dict[str, Any],
                                 Optional["TaskResult"],
                                 Namespace,
                                 "Task")


def _gen_pairs_from_slots_object(obj: Union["Task", "TaskResult"]) -> Tuple[Tuple[str, Any], ...]:
    """Generate tuple of attribute name-value pairs from object that defines
    the __slots__ variable.
    Raises:
        TypeError: if obj doesn't define __slots__
    """
    if not hasattr(obj, "__slots__"):
        raise TypeError("{} does not define __slots__".format(type(obj).__name__))
    return tuple((attr_name, getattr(obj, attr_name))
                 for attr_name in dir(obj)
                 if not attr_name.startswith("_") and not callable(getattr(obj, attr_name)))


def _gen_pairs_from_object(obj: StatePropogationSource) -> Union[Tuple[()], Tuple[Tuple[str, Any], ...]]:
    """Generate tuple of attribute name-value pairs from supported types.
    Raises:
        TypeError: If obj is not a supported type
    """
    if obj is None:
        items: Union[Tuple[()], Tuple[Tuple[str, Any], ...]] = tuple()
    elif isinstance(obj, dict):
        items = tuple(obj.items())
    elif isinstance(obj, Namespace):
        items = tuple(obj._get_kwargs())
    elif isinstance(obj, Task):
        items = tuple() if obj.state is None else tuple(obj.state.items())
        items = items + _gen_pairs_from_slots_object(obj)
    elif isinstance(obj, TaskResult):
        items = _gen_pairs_from_slots_object(obj)
    else:
        raise TypeError("Cannot generate name-value pairs from type {}".format(type(obj).__name__))
    return items


class TaskResult:
    """Result of running a task.  Used to pass result data to other compatible
    tasks, and defined on a per-task basis. Base task result passes the Exception
    raised from running a task, if one occurred.
    """
    __slots__ = ("err",)

    def __init__(self, err: Optional[Exception] = None) -> None:
        self.err = err


class Task:
    """Base class for all tasks. Implements basic functionality for each task
    including initializing/updating state from objects, chaining tasks together,
    and running the task.
    """
    __slots__ = ("state", "result")

    _EXCLUDE_FROM_MERGE: ClassVar[Set[str]] = set()

    @staticmethod
    def gen_task_result() -> TaskResult:
        """
        Args:
            N/A
        Returns:
            Instance of task result for this task.  Default implementation returns
            empty TaskResult.  All child class implementations are responsible for overriding
            this method if needed.
        Preconditions:
            N/A
        Raises:
            N/A
        """
        return TaskResult()

    def __init__(self, state: Optional[Dict[str, Any]] = None, result: Optional[TaskResult] = None) -> None:
        self.state: Optional[Dict[str, Any]] = state
        self.result: Optional[TaskResult] = result

    def _postamble(self) -> None:
        """
        Args:
            N/A
        Procedure:
            Perform any necessary cleanup steps after task completes. Default implementation is a NOOP.
            Should _not_ raise an exception, as this method always runs even if task fails.
        Preconditions:
            Does not raise an exception
        Raises:
            N/A
        """

    def _perform_task(self) -> None:
        """
        Args:
            N/A
        Procedure:
            Perform main steps of task and (optionally) set self.result.  Tasks _must_
            implement this method.
        Preconditions:
            N/A
        """
        raise NotImplementedError("_perform_task not implemented for {}".format(type(self).__name__))

    def _preamble(self) -> None:
        """
        Args:
            N/A
        Procedure:
            Perform setup steps before running the task.  Default implementation is NOOP.
            Should _not_ raise an exception, as this method always runs even if task fails.
        Preconditions:
            Does not raise an exception
        Raises:
            N/A
        """

    def run(self) -> Optional[TaskResult]:
        """
        Args:
            N/A
        Returns:
            Result after running this task.
        Preconditions:
            N/A
        Raises:
            See: _perform_task
        """
        task_type = type(self).__name__
        logger.info("Running task {}".format(task_type))
        # Run preamble
        self._preamble()
        try:
            # Run the task
            self._perform_task()
            logger.info("Finished running task {}".format(task_type))
        except Exception as exc:
            # If failed to run task, set err on result
            logger.error("Failed to run task {} ({})".format(task_type, exc))
            if self.result is None:
                self.result = self.gen_task_result()
            self.result.err = exc
        # Run postamble
        self._postamble()
        return self.result

    def _merge_value_with_name(self, name: str, value: Any) -> None:
        """
        Args:
            name    => name of field to set value on
            value   => value to set
        Procedure:
            If name corresponds to field defined on class, set field to value.
            Otherwise, merge name-value pair into state.
        Preconditions:
            N/A
        Raises:
            N/A
        """
        # If name is state or result, don't merge
        if name in {"result", "state"}:
            return
        # Else if name corresponds to field defined on class, set value on field
        if hasattr(type(self), name):
            setattr(self, name, value)
        # Otherwise, merge into state
        else:
            if self.state is None:
                self.state = dict()
            self.state[name] = value

    def merge_object(self,
        obj: StatePropogationSource,
        include: Optional[Set[str]] = None,
        exclude: Optional[Set[str]] = None,
        overwrite: Optional[Dict[str, Any]] = None) -> "Task":
        """
        Args:
            obj         => object to merge
            include     => attributes/values to merge
            exclude     => attributes/values to not merge
            overwrite   => overwrite values in state after merging
        Procedure:
            Initialize/update self by merging values from an object.  If both include and exclude
            are specified, exclude will take priority and include will be ignored.
            Default implementation merges the following:
                Namespace: all kwargs
                Task: all key-value pairs in state plus any other variables defined in __slots__
                TaskResult: all attributes defined in __slots__
            NOTE: The overwrite dict, if provided, is always merged after merging from obj.
            NOTE: All attributes with names other than fields defined in __slots__ will be merged into state
        Preconditions:
            N/A
        Raises:
            N/A
        """
        # Generate items iterable based on type of obj
        items = _gen_pairs_from_object(obj)
        # Set whether exclude and include given
        exclude_given = bool(exclude)
        include_given = bool(include)
        # If exclude is defined, takes precedence over include
        if exclude_given and include_given:
            include = None
            include_given = False
        # Merge exclude with _EXCLUDE_FROM_MERGE static variable
        exclude = (exclude or set()) | self._EXCLUDE_FROM_MERGE
        if bool(exclude):
            exclude_given = True
        exclude_include_given = exclude_given or include_given
        # For each name-value pair in items
        for name, value in items:
            # Merge name-value pair if:
            #   1) Neither exclude nor include (nor _EXCLUDE_FROM_MERGE) are set
            #   2) Name isn't in exclude, _and_
            #     a. include isn't provided
            #     b. name is in include
            if (not exclude_include_given or
                (name not in exclude and (not include_given or name in include))):  # type: ignore
                self._merge_value_with_name(name, value)
        # Merge overwrite
        if overwrite is not None:
            for name, value in overwrite.items():
                self._merge_value_with_name(name, value)
        return self

    def __ror__(self, task_result: Optional[TaskResult]) -> Optional[TaskResult]:
        """
        Args:
            task_result => result from another task
        Returns:
            Result from running this task.  Overloads the `|` operator to enable writing
            pipelines of tasks like the following:

            (Task1().run() | Task2() | Task3())

            Where the result from each task will propogate through the pipeline to the next
            task. This requires that the __or__ function is not defined on any tasks, as Python
            will then not call the __ror__ function.
        Preconditions:
            N/A
        Raises:
            N/A
        """
        self.merge_object(task_result)
        return self.run()
