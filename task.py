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


from argparse import ArgumentParser, Namespace
import logging
import os
import sys
from typing import Any, ClassVar, Dict, List, Optional, Set, Tuple, TypeVar, Union

import argparse_utils as aputils


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
        if hasattr(self, name):
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


class CLITask(Task):    # pylint: disable=abstract-method
    """Base task for tasks that can be instantiated via command line
    using argparse. Supports specifying a 'path' to the subcommand
    for this task. This can be utilized in something like a
    task registry (see: https://github.com/libcommon/registry-py) to allow
    each task to define it's own CLI, but to have the registry attach each
    parser to a parent parser instance.
    """
    __slots__ = ()

    COMMAND: Optional[str] = None
    DESCRIPTION: Optional[str] = None
    _COMMAND_PATH: ClassVar[Optional[Tuple[Tuple[str, Optional[str]], ...]]] = None

    @classmethod
    def configure_command_parser(cls, parser: Optional[ArgumentParser] = None) -> ArgumentParser:
        """
        Args:
            parser  => parent command line parser
        Returns:
            CL argument parser defined either as the primary command or as a subcommand
            at _COMMAND_PATH.
        Preconditions:
            N/A
        Raises:
            ValueError: if COMMAND and DESCRIPTION not defined
        """
        if not (bool(cls.COMMAND) and bool(cls.DESCRIPTION)):
            raise ValueError("COMMAND and DESCRIPTION class variables must be defined")
        # If parser is None, initialize with COMMAND and DESCRIPTION and return
        if parser is None:
            parser = ArgumentParser(prog=cls.COMMAND, description=cls.DESCRIPTION)
            return parser
        subcommand_parser = parser
        # If command path is defined, traverse subcommands creating each subcommand if it does not exist already
        if cls._COMMAND_PATH is not None:
            for command, description in cls._COMMAND_PATH:
                # If parser does not have subcommands or command is not in subcommands, create it
                subcommand_parser = aputils.add_subcommand(subcommand_parser, command, description)
        # Create final subcommand and return
        aputils.add_subcommand(subcommand_parser, cls.COMMAND, cls.DESCRIPTION)     # type: ignore
        return parser

    def run_command(self, argv: List[str] = sys.argv, known_args: bool = False) -> Optional[TaskResult]:    # pylint: disable=dangerous-default-value
        """
        Args:
            argv        => command line args
            known_args  => only parse known args
        Procedure:
            Parse command line args and run task.
        Preconditions:
            N/A
        Raises:
            N/A
        """
        parser = self.configure_command_parser()
        if known_args:
            args, _ = parser.parse_known_args(argv)
        else:
            args = parser.parse_args(argv)
        self.merge_object(args)
        return self.run()


if os.environ.get("ENVIRONMENT") == "TEST":
    import unittest
    import unittest.mock as mock


    class TestTaskResult(TaskResult):
        __slots__ = ("foo",)

        def __init__(self, foo: str = "bar", **kwargs):
            super().__init__(**kwargs)
            self.foo = foo


    class TestTask(Task):   # pylint: disable=abstract-method
        __slots__ = ("foo",)

        def __init__(self, foo: str = "bar"):
            super().__init__()
            self.foo = foo


    class TestCLITask(CLITask):     # pylint: disable=abstract-method
        __slots__ = ()

        COMMAND = "test"
        DESCRIPTION = "Test subcommand"
        _COMMAND_PATH = None


    class HopTestCLITask(CLITask):  # pylint: disable=abstract-method
        __slots__ = ()

        COMMAND = TestCLITask.COMMAND
        DESCRIPTION = TestCLITask.DESCRIPTION
        _COMMAND_PATH = (("hop", "and you don't stop"),)


    class HopScotchTestCLITask(CLITask):    # pylint: disable=abstract-method
        __slots__ = ()

        COMMAND = TestCLITask.COMMAND
        DESCRIPTION = TestCLITask.DESCRIPTION
        _COMMAND_PATH = HopTestCLITask._COMMAND_PATH + (("scotch", "butter"),)

        @classmethod
        def configure_command_parser(cls, parser: Optional[ArgumentParser] = None) -> ArgumentParser:
            parser = super().configure_command_parser(parser)
            parser.add_argument("-n", "--name", required=True, type=str, help="Person's name")
            return parser

        def _perform_task(self) -> None:
            pass


    class TestUtilityMethods(unittest.TestCase):
        """Tests for utility methods for generating name-value pairs from objects."""

        def setUp(self):
            self.maxDiff = None     # pylint: disable=invalid-name

        def test_gen_pairs_from_slots_object(self):
            type_err = TypeError("This is a type error")

            tests = [
                ("TaskResult without error", TaskResult(), (("err", None),)),
                ("TaskResult with error", TaskResult(err=type_err), (("err", type_err),)),
                ("TestTaskResult with default foo", TestTaskResult(), (("err", None), ("foo", "bar")))
            ]

            for test_name, input_object, expected in tests:
                with self.subTest(test_name=test_name):
                    self.assertEqual(tuple(sorted(expected)), tuple(sorted(_gen_pairs_from_slots_object(input_object))))

        def test_gen_pairs_from_object(self):
            test_state = dict(foo="bar", bar="foo")
            task_with_state = Task()
            task_with_state.state = dict(test_state)

            tests = [
                ("None", None, tuple()),
                ("Dict[str, Any]", test_state, (("foo", "bar"), ("bar", "foo"))),
                ("Namespace", Namespace(**test_state), (("foo", "bar"), ("bar", "foo"))),
                ("Task without state", Task(), (("state", None), ("result", None))),
                ("Task with state",
                 task_with_state,
                 (("state", dict(foo="bar", bar="foo")), ("result", None), ("foo", "bar"), ("bar", "foo"))),
                ("TaskResult", TaskResult(), (("err", None),))
            ]

            for test_name, input_object, expected in tests:
                with self.subTest(test_name=test_name):
                    self.assertEqual(tuple(sorted(expected)), tuple(sorted(_gen_pairs_from_object(input_object))))

        def test_merge_value_with_name_to_state(self):
            task = TestTask()

            tests = [
                ("Merging name state", ("state", dict(name="Charlie")), None),
                ("Merging name result", ("result", TaskResult()), None),
                ("Merging name bar to state", ("bar", "foo"), dict(bar="foo")),
            ]

            for test_name, input_object, expected in tests:
                with self.subTest(test_name=test_name):
                    name, value = input_object
                    task._merge_value_with_name(name, value)
                    self.assertEqual(expected, task.state)

        def test_merge_value_with_name_to_attribute(self):
            task = TestTask()
            task._merge_value_with_name("foo", "barrio")
            self.assertEqual("barrio", task.foo)

        def test_task_merge_object(self):
            task_to_merge = TestTask(foo="kitchen")
            task_to_merge.state = dict(color="orange")
            test_state = dict(foo="barrio", bar="foo")

            tests = [
                ("None", None, lambda t: t.state is None and t.foo == "bar"),
                ("Dict[str, Any]", test_state, lambda t: t.state == dict(bar="foo") and t.foo == "barrio"),
                ("Namespace",
                 Namespace(apple="granny smith", foo="barrio"),
                 lambda t: t.state == dict(apple="granny smith") and t.foo == "barrio"),
                ("Task without state",
                 TestTask(foo="bandito"),
                 lambda t: t.state is None and t.foo == "bandito"),
                ("Task with state",
                 task_to_merge,
                 lambda t: t.state == dict(color="orange") and t.foo == "kitchen"),
                ("TaskResult", TestTaskResult(foo="barrio"), lambda t: t.state == dict(err=None) and t.foo == "barrio")
            ]

            for test_name, input_object, condition in tests:
                with self.subTest(test_name=test_name):
                    self.assertTrue(condition(TestTask().merge_object(input_object)))

        def test_task_merge_object_include_exclude(self):

            class TestTaskWithExclude(Task):    # pylint: disable=abstract-method
                __slots__ = ()
                _EXCLUDE_FROM_MERGE = {"color"}

            dict_to_merge = dict(bar="foo", color="red", apple="honey crisp")

            tests = [
                ("Include not in dict", dict(include={"foo"}), lambda t: t.state is None and t.foo == "bar"),
                ("Include in dict (bar)",
                 dict(include={"bar"}),
                 lambda t: t.state == dict(bar="foo") and t.foo == "bar"),
                ("Include in dict (bar, color)",
                 dict(include={"bar", "color"}),
                 lambda t: t.state == dict(bar="foo", color="red") and t.foo == "bar"),
                ("Exclude not in dict", dict(exclude={"foo"}), lambda t: t.state == dict_to_merge and t.foo == "bar"),
                ("Exclude in dict (bar)",
                 dict(exclude={"bar"}),
                 lambda t: t.state == dict(color="red", apple="honey crisp") and t.foo == "bar"),
                ("Exclude in dict (bar, color)",
                 dict(exclude={"bar", "color"}),
                 lambda t: t.state == dict(apple="honey crisp") and t.foo == "bar"),
                ("Exclude and include (bar, color)",
                 dict(include={"bar", "color"}, exclude={"bar", "color"}),
                 lambda t: t.state == dict(apple="honey crisp") and t.foo == "bar")
            ]

            for test_name, kwargs, condition in tests:
                with self.subTest(test_name=test_name):
                    task = TestTask().merge_object(dict_to_merge, **kwargs)
                    self.assertTrue(condition(task))

            with self.subTest(test_name="Exclude with _EXCLUDE_FROM_MERGE"):
                task = TestTaskWithExclude()
                task.merge_object(dict_to_merge)
                self.assertTrue(task.state == dict(bar="foo", apple="honey crisp"))

        def test_task_ror_merge_object(self):
            with mock.patch.object(Task, "run"):
                err = IOError("this is an IO error")
                task_result = TestTaskResult(err=err, foo="barrio")
                next_task = TestTask()
                (task_result | next_task)   # pylint: disable=pointless-statement
                self.assertTrue(next_task.state == dict(err=err) and next_task.foo == "barrio")

        def test_clitask_gen_parser(self):
            tests = [
                ("Without root parser",
                 None,
                 TestCLITask,
                 (TestCLITask.COMMAND, TestCLITask.DESCRIPTION)),
                ("With root parser, path is None",
                 ArgumentParser(prog="test", description="This is a test parser"),
                 TestCLITask,
                 ("test test", TestCLITask.DESCRIPTION)),
                ("With root parser, path is hop",
                 ArgumentParser(prog="test", description="This is a test parser"),
                 HopTestCLITask,
                 ("test hop test", HopTestCLITask.DESCRIPTION)),
                ("With root parser, path is hop -> scotch",
                 ArgumentParser(prog="test", description="This is a test parser"),
                 HopScotchTestCLITask,
                 ("test hop scotch test", HopScotchTestCLITask.DESCRIPTION))
            ]

            for test_name, parser, task_cls, condition in tests:
                with self.subTest(test_name=test_name):
                    task_cls().configure_command_parser(parser)
                    prog, description = condition
                    if parser is not None:
                        command_path = prog.split(" ")[1:]
                        subcommand = parser
                        while subcommand is not None and bool(command_path):
                            subcommand = aputils.get_subcommand(subcommand, command_path.pop(0))
                        self.assertTrue(subcommand is not None)
                        self.assertEqual(subcommand.prog, prog)
                        self.assertEqual(subcommand.description, description)

        def test_clitask_run_command_all_args(self):
            with mock.patch.object(TestCLITask, "run"):
                task = HopScotchTestCLITask()
                argv = ["-n", "Adam"]
                task.run_command(argv=argv)
                self.assertEqual("Adam", task.state.get("name"))

        def test_clitask_run_command_known_args(self):
            with mock.patch.object(TestCLITask, "run"):
                task = HopScotchTestCLITask()
                argv = ["-n", "Adam", "--key", "this_key"]
                task.run_command(argv=argv, known_args=True)
                self.assertEqual("Adam", task.state.get("name"))
