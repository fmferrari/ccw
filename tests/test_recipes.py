from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ccw.recipe import Recipe, Section, get_recipe, allocate_budget


class RecipeLookupTests(unittest.TestCase):
    def test_get_recipe_bugfix(self) -> None:
        recipe = get_recipe("bugfix")
        self.assertEqual(recipe.mode, "bugfix")

    def test_get_recipe_implementation(self) -> None:
        recipe = get_recipe("implementation")
        self.assertEqual(recipe.mode, "implementation")

    def test_get_recipe_review(self) -> None:
        recipe = get_recipe("review")
        self.assertEqual(recipe.mode, "review")

    def test_get_recipe_refactor(self) -> None:
        recipe = get_recipe("refactor")
        self.assertEqual(recipe.mode, "refactor")

    def test_get_recipe_case_insensitive(self) -> None:
        self.assertEqual(get_recipe("BUGFIX").mode, "bugfix")
        self.assertEqual(get_recipe("Implementation").mode, "implementation")
        self.assertEqual(get_recipe("Review").mode, "review")
        self.assertEqual(get_recipe("REFACTOR").mode, "refactor")

    def test_get_recipe_unknown_mode_falls_back_to_implementation(self) -> None:
        recipe = get_recipe("unknown")
        self.assertEqual(recipe.mode, "implementation")

    def test_get_recipe_empty_string_falls_back_to_implementation(self) -> None:
        recipe = get_recipe("")
        self.assertEqual(recipe.mode, "implementation")

    def test_get_recipe_whitespace_stripped(self) -> None:
        recipe = get_recipe("  bugfix  ")
        self.assertEqual(recipe.mode, "bugfix")


class RecipeDefinitionTests(unittest.TestCase):
    def test_all_recipes_have_required_sections(self) -> None:
        required = {"files", "symbols", "edges", "facts", "episodes", "constraints"}
        for mode in ("bugfix", "implementation", "review", "refactor"):
            with self.subTest(mode=mode):
                recipe = get_recipe(mode)
                self.assertIn("files", recipe.sections)
                self.assertIn("symbols", recipe.sections)
                self.assertIn("edges", recipe.sections)
                self.assertIn("facts", recipe.sections)
                self.assertIn("episodes", recipe.sections)
                self.assertIn("constraints", recipe.sections)
                for section in recipe.sections.values():
                    self.assertIsInstance(section, Section)
                    self.assertGreater(section.weight, 0)
                    self.assertGreaterEqual(section.min_budget, 0)
                    self.assertGreater(section.max_items, 0)

    def test_each_recipe_has_default_total_budget(self) -> None:
        for mode in ("bugfix", "implementation", "review", "refactor"):
            with self.subTest(mode=mode):
                recipe = get_recipe(mode)
                self.assertGreater(recipe.total_budget, 0)

    def test_bugfix_has_smallest_budget(self) -> None:
        bugfix = get_recipe("bugfix")
        impl = get_recipe("implementation")
        review = get_recipe("review")
        self.assertLessEqual(
            bugfix.total_budget,
            min(impl.total_budget, review.total_budget),
        )

    def test_refactor_has_largest_budget(self) -> None:
        refactor = get_recipe("refactor")
        for mode in ("bugfix", "implementation", "review"):
            other = get_recipe(mode)
            self.assertGreaterEqual(refactor.total_budget, other.total_budget)

    def test_recipes_are_deterministic(self) -> None:
        for mode in ("bugfix", "implementation", "review", "refactor"):
            with self.subTest(mode=mode):
                self.assertIs(get_recipe(mode), get_recipe(mode))

    def test_implementation_is_default_recipe(self) -> None:
        default = get_recipe("implementation")
        for mode in ("", "  ", "nosuchmode"):
            self.assertIs(get_recipe(mode), default)


class BudgetAllocationTests(unittest.TestCase):
    def test_default_budget_distribution(self) -> None:
        recipe = get_recipe("implementation")
        budget = allocate_budget(recipe)
        total = sum(budget.values())
        self.assertLessEqual(total, recipe.total_budget)

    def test_custom_budget_scales_proportionally(self) -> None:
        recipe = get_recipe("implementation")
        custom = 4000
        budget = allocate_budget(recipe, total_budget=custom)
        total = sum(budget.values())
        self.assertLessEqual(total, custom)

    def test_custom_budget_larger_than_default(self) -> None:
        recipe = get_recipe("bugfix")
        custom = 12000
        budget = allocate_budget(recipe, total_budget=custom)
        total = sum(budget.values())
        self.assertLessEqual(total, custom)

    def test_budget_falls_below_min_budget_sum(self) -> None:
        recipe = get_recipe("bugfix")
        tiny = 100
        budget = allocate_budget(recipe, total_budget=tiny)
        min_sum = sum(s.min_budget for s in recipe.sections.values())
        total = sum(budget.values())
        self.assertEqual(total, min_sum)
        for section in recipe.sections.values():
            self.assertEqual(budget[section.name], section.min_budget)

    def test_budget_equals_min_budget_sum(self) -> None:
        recipe = get_recipe("review")
        min_sum = sum(s.min_budget for s in recipe.sections.values())
        budget = allocate_budget(recipe, total_budget=min_sum)
        total = sum(budget.values())
        self.assertEqual(total, min_sum)
        for section in recipe.sections.values():
            self.assertEqual(budget[section.name], section.min_budget)

    def test_each_section_meets_minimum(self) -> None:
        recipe = get_recipe("refactor")
        budget = allocate_budget(recipe)
        for section in recipe.sections.values():
            self.assertGreaterEqual(budget[section.name], section.min_budget)

    def test_each_section_given_from_all_modes_meets_minimum(self) -> None:
        for mode in ("bugfix", "implementation", "review", "refactor"):
            with self.subTest(mode=mode):
                recipe = get_recipe(mode)
                budget = allocate_budget(recipe)
                for section in recipe.sections.values():
                    self.assertGreaterEqual(
                        budget[section.name],
                        section.min_budget,
                        f"Section {section.name} in mode {mode} below minimum",
                    )

    def test_remainder_distribution_goes_to_highest_weight(self) -> None:
        recipe = get_recipe("review")
        budget = allocate_budget(recipe, total_budget=5000)
        files_weight = recipe.sections["files"].weight
        symbols_weight = recipe.sections["symbols"].weight
        self.assertGreaterEqual(budget["files"], budget["symbols"])

    def test_all_sections_present_in_allocation(self) -> None:
        for mode in ("bugfix", "implementation", "review", "refactor"):
            with self.subTest(mode=mode):
                recipe = get_recipe(mode)
                budget = allocate_budget(recipe)
                self.assertEqual(set(budget.keys()), set(recipe.sections.keys()))

    def test_allocate_budget_is_deterministic(self) -> None:
        recipe = get_recipe("implementation")
        self.assertEqual(
            allocate_budget(recipe, total_budget=5000),
            allocate_budget(recipe, total_budget=5000),
        )

    def test_zero_budget_allocates_minimums(self) -> None:
        recipe = get_recipe("bugfix")
        budget = allocate_budget(recipe, total_budget=0)
        for section in recipe.sections.values():
            self.assertEqual(budget[section.name], section.min_budget)

    def test_exact_budget_no_remainder_waste(self) -> None:
        recipe = get_recipe("implementation")
        budget = allocate_budget(recipe, total_budget=recipe.total_budget)
        total = sum(budget.values())
        self.assertLessEqual(total, recipe.total_budget)
        self.assertGreaterEqual(total, recipe.total_budget - len(recipe.sections))


if __name__ == "__main__":
    unittest.main()
