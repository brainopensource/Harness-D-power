---
status: normative
updated: 2026-08-07
---

# SWE-bench Verified — 15-Task Stratified Beta Sample

This document maps the **15-task random sample** selected from `princeton-nlp/SWE-bench_Verified` for early harness testing and beta evaluation (75% confidence interval, ±15% margin of error).

**Note:** No repositories or assets have been downloaded yet. This document contains only dataset indexing and metadata mapping for future content-addressed resolution via `TASK-010` (`repo_cache.py`).

## 📊 Sample Summary

| Stratum | Task Count | Repositories Covered | Target Complexity |
| :--- | :---: | :--- | :--- |
| **Easy** | 5 | Django, SymPy, Scikit-learn, Sphinx, Astropy | Single-file / ≤25 line fix |
| **Medium** | 5 | Django, Requests, Pytest, Sphinx, Scikit-learn | Multi-file / 25–80 line fix |
| **Hard** | 5 | Django, SymPy, Scikit-learn, Sphinx, Matplotlib | Complex multi-file refactor / >80 line fix |
| **Total** | **15** | **7 Unique OSS Python Repos** | **3.0% of 500-task Verified Suite** |

---

## 🛠️ Task Mapping Table

| Index | Difficulty | Task ID | Repository | GitHub Issue URL | Base Commit SHA | Patch Size (Lines / Files) |
| :---: | :---: | :--- | :--- | :--- | :--- | :---: |
| 1 | **Easy** | `sympy__sympy-12096` | `sympy/sympy` | [#12096](https://github.com/sympy/sympy/issues/12096) | `d7c3045115` | ~12 lines / 1 file(s) |
| 2 | **Easy** | `django__django-13590` | `django/django` | [#13590](https://github.com/django/django/issues/13590) | `755dbf39fc` | ~19 lines / 1 file(s) |
| 3 | **Easy** | `psf__requests-6028` | `psf/requests` | [#6028](https://github.com/psf/requests/issues/6028) | `0192aac241` | ~14 lines / 1 file(s) |
| 4 | **Easy** | `sphinx-doc__sphinx-7910` | `sphinx-doc/sphinx` | [#7910](https://github.com/sphinx-doc/sphinx/issues/7910) | `27ac10de04` | ~20 lines / 1 file(s) |
| 5 | **Easy** | `django__django-11951` | `django/django` | [#11951](https://github.com/django/django/issues/11951) | `3120490912` | ~13 lines / 1 file(s) |
| 6 | **Medium** | `pylint-dev__pylint-4604` | `pylint-dev/pylint` | [#4604](https://github.com/pylint-dev/pylint/issues/4604) | `1e55ae6462` | ~33 lines / 2 file(s) |
| 7 | **Medium** | `sympy__sympy-21596` | `sympy/sympy` | [#21596](https://github.com/sympy/sympy/issues/21596) | `110997fe18` | ~62 lines / 1 file(s) |
| 8 | **Medium** | `scikit-learn__scikit-learn-26194` | `scikit-learn/scikit-learn` | [#26194](https://github.com/scikit-learn/scikit-learn/issues/26194) | `e886ce4e14` | ~46 lines / 1 file(s) |
| 9 | **Medium** | `pydata__xarray-6744` | `pydata/xarray` | [#6744](https://github.com/pydata/xarray/issues/6744) | `7cc6cc991e` | ~31 lines / 1 file(s) |
| 10 | **Medium** | `django__django-14053` | `django/django` | [#14053](https://github.com/django/django/issues/14053) | `179ee13eb3` | ~43 lines / 1 file(s) |
| 11 | **Hard** | `django__django-16263` | `django/django` | [#16263](https://github.com/django/django/issues/16263) | `321ecb40f4` | ~227 lines / 4 file(s) |
| 12 | **Hard** | `sympy__sympy-13091` | `sympy/sympy` | [#13091](https://github.com/sympy/sympy/issues/13091) | `d1320814ed` | ~522 lines / 21 file(s) |
| 13 | **Hard** | `matplotlib__matplotlib-25775` | `matplotlib/matplotlib` | [#25775](https://github.com/matplotlib/matplotlib/issues/25775) | `26224d9606` | ~132 lines / 3 file(s) |
| 14 | **Hard** | `pylint-dev__pylint-4551` | `pylint-dev/pylint` | [#4551](https://github.com/pylint-dev/pylint/issues/4551) | `99589b08de` | ~187 lines / 4 file(s) |
| 15 | **Hard** | `pydata__xarray-6938` | `pydata/xarray` | [#6938](https://github.com/pydata/xarray/issues/6938) | `c4e40d991c` | ~91 lines / 2 file(s) |

---

## 📑 Detailed Task Specifications

### Task 1: `sympy__sympy-12096`
* **Difficulty**: **Easy**
* **Repository**: `sympy/sympy`
* **Base Commit**: `d7c3045115693e887bcd03599b7ca4650ac5f2cb`
* **Repo Clone URL**: `https://github.com/sympy/sympy.git`
* **Problem Summary**:
  > evalf does not call _imp_ recursively Example from https://stackoverflow.com/questions/41818842/why-cant-i-evaluate-a-composition-of-implemented-functions-in-sympy-at-a-point:  ``` >>> from sympy.utilities.lambdify import implemented_function >>> f = implemented_function('f', lambda x: x ** 2) >>> g = implemented_function('g', lambda x: 2 * x)...

### Task 2: `django__django-13590`
* **Difficulty**: **Easy**
* **Repository**: `django/django`
* **Base Commit**: `755dbf39fcdc491fe9b588358303e259c7750be4`
* **Repo Clone URL**: `https://github.com/django/django.git`
* **Problem Summary**:
  > Upgrading 2.2>3.0 causes named tuples used as arguments to __range to error. Description 	 I noticed this while upgrading a project from 2.2 to 3.0. This project passes named 2-tuples as arguments to range queryset filters. This works fine on 2.2. On 3.0 it causes the following error: TypeError: __new__() missing 1 required positional argument: 'fa...

### Task 3: `psf__requests-6028`
* **Difficulty**: **Easy**
* **Repository**: `psf/requests`
* **Base Commit**: `0192aac24123735b3eaf9b08df46429bb770c283`
* **Repo Clone URL**: `https://github.com/psf/requests.git`
* **Problem Summary**:
  > Proxy authentication bug <!-- Summary. -->  When using proxies in python 3.8.12, I get an error 407. Using any other version of python works fine. I am assuming it could be to do with this https://docs.python.org/3/whatsnew/3.8.html#notable-changes-in-python-3-8-12.  <!-- What you expected. -->  I should get a status of 200.  <!-- What happ...

### Task 4: `sphinx-doc__sphinx-7910`
* **Difficulty**: **Easy**
* **Repository**: `sphinx-doc/sphinx`
* **Base Commit**: `27ac10de04697e2372d31db5548e56a7c6d9265d`
* **Repo Clone URL**: `https://github.com/sphinx-doc/sphinx.git`
* **Problem Summary**:
  > Decorated __init__ doesn't show up in docs Subject: Decorated __init__ won't be documented. I'm working on `tensorpack` (`github.com/ppwwyyxx/tensorpack`)  ### Problem - I have `napoleon_include_init_with_doc = True`, so `__init__` will be documented. But if I decorate the `__init__` method, it will not show up in docs. I decorate it with `functoo...

### Task 5: `django__django-11951`
* **Difficulty**: **Easy**
* **Repository**: `django/django`
* **Base Commit**: `312049091288dbba2299de8d07ea3e3311ed7238`
* **Repo Clone URL**: `https://github.com/django/django.git`
* **Problem Summary**:
  > bulk_create batch_size param overrides the compatible batch size calculation Description 	  		(last modified by Ahmet Kucuk) 	  At this line: ​https://github.com/django/django/blob/stable/2.2.x/django/db/models/query.py#L1197 batch_size param overrides compatible batch size calculation. This looks like a bug as bulk_update properly picks the minimu...

### Task 6: `pylint-dev__pylint-4604`
* **Difficulty**: **Medium**
* **Repository**: `pylint-dev/pylint`
* **Base Commit**: `1e55ae64624d28c5fe8b63ad7979880ee2e6ef3f`
* **Repo Clone URL**: `https://github.com/pylint-dev/pylint.git`
* **Problem Summary**:
  > unused-import false positive for a module used in a type comment ### Steps to reproduce  ```python """Docstring."""  import abc from abc import ABC  X = ...  # type: abc.ABC Y = ...  # type: ABC ```  ### Current behavior  ``` ************* Module a /tmp/a.py:3:0: W0611: Unused import abc (unused-import)  --------------------------...

### Task 7: `sympy__sympy-21596`
* **Difficulty**: **Medium**
* **Repository**: `sympy/sympy`
* **Base Commit**: `110997fe18b9f7d5ba7d22f624d156a29bf40759`
* **Repo Clone URL**: `https://github.com/sympy/sympy.git`
* **Problem Summary**:
  > bug in is_subset(Reals) Solving issue #19513 has given rise to another bug. Now: ``` In [8]: S1 = imageset(Lambda(n, n + (n - 1)*(n + 1)*I), S.Integers)  In [9]: S1 Out[9]: {n + ⅈ⋅(n - 1)⋅(n + 1) │ n ∊ ℤ}  In [10]: 2 in S1 Out[10]: False  In [11]: 2 in S1.intersect(Reals) Out[11]: True ``` This output is incorrect.  Correct output i...

### Task 8: `scikit-learn__scikit-learn-26194`
* **Difficulty**: **Medium**
* **Repository**: `scikit-learn/scikit-learn`
* **Base Commit**: `e886ce4e1444c61b865e7839c9cff5464ee20ace`
* **Repo Clone URL**: `https://github.com/scikit-learn/scikit-learn.git`
* **Problem Summary**:
  > Thresholds can exceed 1 in `roc_curve` while providing probability estimate While working on https://github.com/scikit-learn/scikit-learn/pull/26120, I found out that something was odd with `roc_curve` that returns a threshold greater than 1. A non-regression test (that could be part of `sklearn/metrics/tests/test_ranking.py`) could be as follow: ...

### Task 9: `pydata__xarray-6744`
* **Difficulty**: **Medium**
* **Repository**: `pydata/xarray`
* **Base Commit**: `7cc6cc991e586a6158bb656b8001234ccda25407`
* **Repo Clone URL**: `https://github.com/pydata/xarray.git`
* **Problem Summary**:
  > "center" kwarg ignored when manually iterating over DataArrayRolling ### Discussed in https://github.com/pydata/xarray/discussions/6738  <div type='discussions-op-text'>  <sup>Originally posted by **ckingdon95** June 29, 2022</sup> Hello, I am trying to manually iterate over a DataArrayRolling object, as described [here ](https://docs.xarray.d...

### Task 10: `django__django-14053`
* **Difficulty**: **Medium**
* **Repository**: `django/django`
* **Base Commit**: `179ee13eb37348cd87169a198aec18fedccc8668`
* **Repo Clone URL**: `https://github.com/django/django.git`
* **Problem Summary**:
  > HashedFilesMixin's post_process() yields multiple times for the same file Description 	 As part of fixing #24452, the implementation of HashedFilesMixin (used by both ManifestStaticFilesStorage and CachedStaticFilesStorage) was changed such that it performs several passes against the found files, therefore ensuring that nested references between th...

### Task 11: `django__django-16263`
* **Difficulty**: **Hard**
* **Repository**: `django/django`
* **Base Commit**: `321ecb40f4da842926e1bc07e11df4aabe53ca4b`
* **Repo Clone URL**: `https://github.com/django/django.git`
* **Problem Summary**:
  > Strip unused annotations from count queries Description 	 The query below produces a SQL statement that includes the Count('chapters'), despite not not being used in any filter operations. Book.objects.annotate(Count('chapters')).count() It produces the same results as: Book.objects.count() Django could be more intelligent about what annotations to...

### Task 12: `sympy__sympy-13091`
* **Difficulty**: **Hard**
* **Repository**: `sympy/sympy`
* **Base Commit**: `d1320814eda6549996190618a21eaf212cfd4d1e`
* **Repo Clone URL**: `https://github.com/sympy/sympy.git`
* **Problem Summary**:
  > Return NotImplemented, not False, upon rich comparison with unknown type Comparison methods should ideally return ``NotImplemented`` when unable to make sense of the arguments. This way, the comparison is delegated to the reflected method on the other object, which might support the comparison (see https://docs.python.org/3/reference/datamodel.html...

### Task 13: `matplotlib__matplotlib-25775`
* **Difficulty**: **Hard**
* **Repository**: `matplotlib/matplotlib`
* **Base Commit**: `26224d96066b5c60882296c551f54ca7732c0af0`
* **Repo Clone URL**: `https://github.com/matplotlib/matplotlib.git`
* **Problem Summary**:
  > [ENH]: Add get/set_antialiased to Text objects ### Problem  Currently, Text objects always retrieve their antialiasing state via the global rcParams["text.antialias"], unlike other artists for which this can be configured on a per-artist basis via `set_antialiased` (and read via `set_antialiased`).  ### Proposed solution  Add similar getters/setter...

### Task 14: `pylint-dev__pylint-4551`
* **Difficulty**: **Hard**
* **Repository**: `pylint-dev/pylint`
* **Base Commit**: `99589b08de8c5a2c6cc61e13a37420a868c80599`
* **Repo Clone URL**: `https://github.com/pylint-dev/pylint.git`
* **Problem Summary**:
  > Use Python type hints for UML generation It seems that pyreverse does not read python type hints (as defined by [PEP 484](https://www.python.org/dev/peps/pep-0484/)), and this does not help when you use `None` as a default value :  ### Code example ``` class C(object):     def __init__(self, a: str = None):         self.a = a ```  ### Curr...

### Task 15: `pydata__xarray-6938`
* **Difficulty**: **Hard**
* **Repository**: `pydata/xarray`
* **Base Commit**: `c4e40d991c28be51de9ac560ce895ac7f9b14924`
* **Repo Clone URL**: `https://github.com/pydata/xarray.git`
* **Problem Summary**:
  > `.swap_dims()` can modify original object ### What happened?  This is kind of a convoluted example, but something I ran into. It appears that in certain cases `.swap_dims()` can modify the original object, here the `.dims` of a data variable that was swapped into being a dimension coordinate variable.  ### What did you expect to happen?  I ex...

---

## ⚙️ How to Download & Run This Sample

When ready to download repositories locally, `TASK-010` (`src/aether/measurement/repo_cache.py`) will ingest this task list and clone **only** the 7 unique repositories for these 15 tasks:

```bash
# 1. Resolve and clone base commits for these 15 tasks only (~3.5 GB on disk)
python scripts/resolve_swebench_bases.py --manifest docs/benchmarks/swe_verified_sample.md

# 2. Run initial beta evaluation pass (75% confidence level, ±15% margin of error)
python -m aether.measurement.runner --manifest docs/benchmarks/swe_verified_sample.md
```
