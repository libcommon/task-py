# pylint: disable=missing-class-docstring,missing-function-docstring
import unittest
from argparse import Namespace
from unittest import mock

from lc_task import Task, TaskResult
from lc_task.task import _gen_pairs_from_object, _gen_pairs_from_slots_object


class TaskResult1(TaskResult):
    __slots__ = ("foo",)

    def __init__(self, foo: str = "bar", **kwargs):
        super().__init__(**kwargs)
        self.foo = foo


class Task1(Task):  # pylint: disable=abstract-method
    __slots__ = ("foo",)

    def __init__(self, foo: str = "bar"):
        super().__init__()
        self.foo = foo


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
        test_state = {"foo": "bar", "bar": "foo"}
        task_with_state = Task()
        task_with_state.state = dict(test_state)

        tests = [
            ("None", None, tuple()),
            ("Dict[str, Any]", test_state, (("foo", "bar"), ("bar", "foo"))),
            ("Namespace", Namespace(**test_state), (("foo", "bar"), ("bar", "foo"))),
            ("Task without state", Task(), (("state", None), ("result", None))),
            (
                "Task with state",
                task_with_state,
                (("state", {"foo": "bar", "bar": "foo"}), ("result", None), ("foo", "bar"), ("bar", "foo")),
            ),
            ("TaskResult", TaskResult(), (("err", None),)),
        ]

        for test_name, input_object, expected in tests:
            with self.subTest(test_name=test_name):
                self.assertEqual(tuple(sorted(expected)), tuple(sorted(_gen_pairs_from_object(input_object))))

    def test_merge_value_with_name_to_state(self):
        task = Task1()

        tests = [
            ("Merging name state", ("state", {"name": "Charlie"}), None),
            ("Merging name result", ("result", TaskResult()), None),
            ("Merging name bar to state", ("bar", "foo"), {"bar": "foo"}),
        ]

        for test_name, input_object, expected in tests:
            with self.subTest(test_name=test_name):
                name, value = input_object
                task._merge_value_with_name(name, value)
                self.assertEqual(expected, task.state)

    def test_merge_value_with_name_to_attribute(self):
        task = Task1()
        task._merge_value_with_name("foo", "barrio")
        self.assertEqual("barrio", task.foo)

    def test_task_merge_object(self):
        task_to_merge = Task1(foo="kitchen")
        task_to_merge.state = {"color": "orange"}
        test_state = {"foo": "barrio", "bar": "foo"}

        tests = [
            ("None", None, lambda t: t.state is None and t.foo == "bar"),
            ("Dict[str, Any]", test_state, lambda t: t.state == {"bar": "foo"} and t.foo == "barrio"),
            (
                "Namespace",
                Namespace(apple="granny smith", foo="barrio"),
                lambda t: t.state == {"apple": "granny smith"} and t.foo == "barrio",
            ),
            ("Task without state", Task1(foo="bandito"), lambda t: t.state is None and t.foo == "bandito"),
            ("Task with state", task_to_merge, lambda t: t.state == {"color": "orange"} and t.foo == "kitchen"),
            ("TaskResult", TaskResult1(foo="barrio"), lambda t: t.state == {"err": None} and t.foo == "barrio"),
        ]

        for test_name, input_object, condition in tests:
            with self.subTest(test_name=test_name):
                self.assertTrue(condition(Task1().merge_object(input_object)))

    def test_task_merge_object_include_exclude(self):
        class TestTaskWithExclude(Task):  # pylint: disable=abstract-method
            __slots__ = ()
            _EXCLUDE_FROM_MERGE = {"color"}  # pylint: disable=invalid-name

        dict_to_merge = {"bar": "foo", "color": "red", "apple": "honey crisp"}

        tests = [
            ("Include not in dict", {"include": {"foo"}}, lambda t: t.state is None and t.foo == "bar"),
            ("Include in dict (bar)", {"include": {"bar"}}, lambda t: t.state == {"bar": "foo"} and t.foo == "bar"),
            (
                "Include in dict (bar, color)",
                {"include": {"bar", "color"}},
                lambda t: t.state == {"bar": "foo", "color": "red"} and t.foo == "bar",
            ),
            ("Exclude not in dict", {"exclude": {"foo"}}, lambda t: t.state == dict_to_merge and t.foo == "bar"),
            (
                "Exclude in dict (bar)",
                {"exclude": {"bar"}},
                lambda t: t.state == {"color": "red", "apple": "honey crisp"} and t.foo == "bar",
            ),
            (
                "Exclude in dict (bar, color)",
                {"exclude": {"bar", "color"}},
                lambda t: t.state == {"apple": "honey crisp"} and t.foo == "bar",
            ),
            (
                "Exclude and include (bar, color)",
                {"include": {"bar", "color"}, "exclude": {"bar", "color"}},
                lambda t: t.state == {"apple": "honey crisp"} and t.foo == "bar",
            ),
            (
                "Exclude with overwrite",
                {"exclude": {"bar"}, "overwrite": {"color": "purple"}},
                lambda t: t.state == {"color": "purple", "apple": "honey crisp"} and t.foo == "bar",
            ),
        ]

        for test_name, kwargs, condition in tests:
            with self.subTest(test_name=test_name):
                task = Task1().merge_object(dict_to_merge, **kwargs)
                self.assertTrue(condition(task))

        with self.subTest(test_name="Exclude with _EXCLUDE_FROM_MERGE"):
            task = TestTaskWithExclude()
            task.merge_object(dict_to_merge)
            self.assertTrue(task.state == {"bar": "foo", "apple": "honey crisp"})

    def test_task_ror_merge_object(self):
        with mock.patch.object(Task, "run"):
            err = IOError("this is an IO error")
            task_result = TaskResult1(err=err, foo="barrio")
            next_task = Task1()
            (task_result | next_task)  # pylint: disable=pointless-statement
            self.assertTrue(next_task.state == {"err": err} and next_task.foo == "barrio")
