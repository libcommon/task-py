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
from typing import Any, ClassVar, Dict, List, Optional, Set, Tuple, TypeVar


__author__ = "libcommon"
logger = logging.getLogger(__name__)    # pylint: disable=C0103
StatePropogationSource = TypeVar("StatePropogationSource", Namespace, "Task", Optional["TaskResult"])


def _gen_items_from_slots(obj: Any) -> Tuple[Tuple[str, Any], ...]:
    """Generate tuple of attribute name-value pairs from object that defines
    the __slots__ variable.
    Raises:
        TypeError: if obj doesn't define __slots__
    """
    if not hasattr(obj, "__slots__"):
        raise TypeError("{} does not define __slots__".format(type(obj).__name__))
    return tuple((attr_name, getattr(obj, attr_name)) for attr_name in obj.__slots__)


class TaskResult:
    """Result of running a task.  Used to pass result data to other compatible
    tasks, and defined on a per-task basis. Base task result passes the Exception
    raised from running a task, if one occurred.
    """
    __slots__ = ("err",)

    def __init__(self, err: Optional[Exception] = None) -> None:
        self.err: Optional[Exception] = err


class Task:
    """Base class for all tasks. Implements basic functionality for each task
    including initializing/updating state from objects, chaining tasks together,
    and running the task.
    """
    __slots__ = ("state", "result")

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
        # If name corresponds to field defined on class, set value on field
        if hasattr(self, name):
            setattr(self, name, value)
        # Otherwise, merge into state
        else:
            if self.state is None:
                self.state = dict()
            self.state[name] = value

    def merge(self,
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
        if obj is None:
            items = None
        elif isinstance(obj, Namespace):
            items = tuple(obj._get_kwargs())
        elif isinstance(obj, Task):
            items = tuple() if obj.state is None else tuple(obj.state.items())
            items = items + _gen_items_from_slots(obj)
        elif isinstance(obj, TaskResult):
            items = _gen_items_from_slots(obj)
        else:
            raise TypeError("{} not supported for merging".format(type(obj).__name__))
        # If items to merge
        if bool(items):
            # If exclude is defined, takes precedence over include
            if bool(exclude):
                # For each name-value pair in items
                for name, value in items:
                    # If name is not excluded
                    if name not in exclude:
                        # Merge name-value pair
                        self._merge_value_with_name(name, value)
            # Else if include defined
            elif bool(include):
                # For each name-value pair in items
                for name, value in items:
                    if name in include:
                        # Merge name-value pair
                        self._merge_value_with_name(name, value)
            # Otherwise, merge all name-value pairs
            else:
                for name, value in items:
                    self._merge_value_with_name(name, value)
        # Merge overwrite
        if bool(overwrite):
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
        self.merge(task_result)
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
    def gen_command_parser(cls, parser: Optional[ArgumentParser] = None) -> ArgumentParser:
        """
        Args:
            parser  => parent command line parser
        Returns:

        Preconditions:
            N/A
        Raises:
            ValueError: if COMMAND and DESCRIPTION not defined
        """
        if not (bool(cls.COMMAND) and bool(cls.DESCRIPTION)):
            raise ValueError("COMMAND and DESCRIPTION class variables must be defined")
        # If parser is None, initialize with COMMAND and DESCRIPTION and return
        if not bool(parser):
            parser = ArgumentParser(prog=cls.COMMAND, description=cls.DESCRIPTION)
            return parser
        # If command path is defined, traverse subcommands to second to last subcommand in path,
        # creating each subcommand if it does not exist already
        if bool(cls._COMMAND_PATH):
            for command, description in cls._COMMAND_PATH:
                # If parser does not have subcommands or command is not in subcommands, create it
                if not bool(parser._subparsers) or len(parser._subparsers._actions) == 1:
                    subparsers = parser.add_subparsers()
                    parser = subparsers.add_parser(command, description=description)
                elif command not in parser._subparsers._actions[1].choices:
                    parser = parser._subparsers._actions[1].add_parser(command, description=description)
                # Otherwise, add description if not set
                else:
                    parser = parser._subparsers._actions[1].choices.get(command)
                    if not bool(parser.description):
                        parser.description = description
        # Create final subcommand and return
        subparsers = parser.add_subparsers()
        parser = subparsers.add_parser(cls.COMMAND, description=cls.DESCRIPTION)
        return parser

    def run_command(self, argv: List[str] = None, known_args: bool = False) -> Optional[TaskResult]:
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
        parser = self.gen_command_parser()
        if known_args:
            args, _ = parser.parse_known_args(argv)
        else:
            args = parser.parse_args(argv)
        self.merge(args)
        return self.run()
