# mypy: disable-error-code="call-arg"
# pylint: disable=missing-class-docstring,missing-function-docstring
import typing
import unittest
from argparse import Namespace
from unittest import mock

from lc_task import Task, TaskResult, taskclass
from lc_task.task import _gen_pairs_from_object, _gen_pairs_from_slots_object


@taskclass
class TaskResult1(TaskResult):
    foo: str = "bar"


@taskclass
class Task1(Task):
    foo: str = "bar"

    def _perform_task(self) -> None:
        pass


class TestTaskAndUtilityMethods(unittest.TestCase):
    """Tests for Task class and associated utility methods."""

    def setUp(self):
        self.maxDiff = None  # pylint: disable=invalid-name

    def test_gen_pairs_from_slots_object(self):
        type_err = TypeError("This is a type error")

        tests = [
            ("TaskResult without error", TaskResult(), (("err", None),)),
            ("TaskResult with error", TaskResult(err=type_err), (("err", type_err),)),
            ("TestTaskResult with default foo", TaskResult1(), (("err", None), ("foo", "bar"))),
        ]

        for test_name, input_object, expected in tests:
            with self.subTest(test_name=test_name):
                self.assertEqual(tuple(sorted(expected)), tuple(sorted(_gen_pairs_from_slots_object(input_object))))

    def test_gen_pairs_from_object(self):
        task = Task1()
        task_result = task.result
        test_dict = {"foo": "baz", "bar": "foo"}

        tests = [
            ("None", None, tuple()),
            ("Dict[str, Any]", test_dict, (("foo", "baz"), ("bar", "foo"))),
            ("Namespace", Namespace(**test_dict), (("bar", "foo"), ("foo", "baz"))),
            (
                "Task",
                task,
                (
                    ("foo", "bar"),
                    ("raise_exceptions", False),
                    ("result", task_result),
                ),
            ),
            ("TaskResult", TaskResult(), (("err", None),)),
        ]

        for test_name, input_object, expected in tests:
            with self.subTest(test_name=test_name):
                self.assertEqual(tuple(sorted(expected)), tuple(sorted(_gen_pairs_from_object(input_object))))

    def test_task_merge_object(self):
        tests = [
            ("None", None, "bar"),
            ("Dict[str, Any]", {"foo": "barrio", "bar": "foo"}, "barrio"),
            (
                "Namespace",
                Namespace(apple="granny smith", foo="barrio"),
                "barrio",
            ),
            ("Task", Task1(foo="bandito"), "bandito"),
            ("TaskResult", TaskResult1(foo="barrio"), "barrio"),
        ]

        for test_name, input_object, expected in tests:
            with self.subTest(test_name=test_name):
                task: Task1 = Task1().merge_object(input_object)
                self.assertEqual(expected, task.foo)

    def test_task_merge_object_include_exclude(self):
        @taskclass
        class TestTaskWithExclude(Task):  # pylint: disable=abstract-method
            _exclude_from_merge = {"color"}

            color: str = "yellow"

            def _perform_task(self) -> None:
                pass

        dict_to_merge = {"foo": "baz", "color": "red", "apple": "honey crisp"}

        tests: typing.List[typing.Tuple[str, typing.Dict[str, typing.Any], str]] = [
            ("Include not in dict", {"include": {"baz"}}, "bar"),
            ("Include in dict (foo)", {"include": {"foo"}}, "baz"),
            (
                "Include in dict not on task (bar, color)",
                {"include": {"bar", "color"}},
                "bar",
            ),
            ("Exclude not in dict", {"exclude": {"bar"}}, "baz"),
            (
                "Exclude in dict (foo)",
                {"exclude": {"foo"}},
                "bar",
            ),
            (
                "Exclude in dict (bar, color)",
                {"exclude": {"apple", "color"}},
                "baz",
            ),
            (
                "Exclude and include equal (foo, color)",
                {"include": {"foo", "color"}, "exclude": {"foo", "color"}},
                "bar",
            ),
            (
                "Exclude with overwrite (foo)",
                {"exclude": {"foo"}, "overwrite": {"foo": "bazinga"}},
                "bazinga",
            ),
        ]

        for test_name, kwargs, expected in tests:
            with self.subTest(test_name=test_name):
                task: Task1 = Task1().merge_object(dict_to_merge, **kwargs)
                self.assertEqual(expected, task.foo)

        with self.subTest(test_name="Exclude with _exclude_from_merge"):
            task_with_exclude: TestTaskWithExclude = TestTaskWithExclude().merge_object(dict_to_merge)
            self.assertEqual("yellow", task_with_exclude.color)

    def test_task_ror_merge_object(self):
        with mock.patch.object(Task, "run"):
            err = IOError("this is an IO error")
            task_result = TaskResult1(err=err, foo="barrio")
            next_task = Task1()
            (task_result | next_task)  # pylint: disable=pointless-statement
            self.assertEqual("barrio", next_task.foo)
