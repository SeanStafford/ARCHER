"""
Integration tests for rendering context - tests real LaTeX compilation.
"""

import os
import shutil
from pathlib import Path

import pytest

from archer.contexts.rendering.compiler import compile_latex, compile_resume

# Check if xelatex is available
XELATEX_AVAILABLE = shutil.which("xelatex") is not None
skip_if_no_xelatex = pytest.mark.skipif(
    not XELATEX_AVAILABLE,
    reason="xelatex not installed - install TeX Live, MiKTeX, or MacTeX"
)


@pytest.mark.integration
@pytest.mark.latex
@skip_if_no_xelatex
@pytest.mark.parametrize(
    "resume_name",
    [
        "Res202506_SenMathLibEng_NVIDIA.tex",
        "Res202507_Anthropic_Pretraining.tex",
        "Res202507_JimG.tex",
    ],
)
def test_compile_historical_resume(resume_name, tmp_path):
    """Test compilation of historical resumes from archive."""
    resume_archive_path = Path(os.getenv("RESUME_ARCHIVE_PATH"))
    resume_file = resume_archive_path / resume_name

    if not resume_file.exists():
        pytest.skip(f"Historical resume not found: {resume_file}")

    compile_dir = tmp_path / "compile"
    compile_dir.mkdir()

    result = compile_latex(resume_file, compile_dir=compile_dir, num_passes=2)

    assert result.success, f"Compilation failed with errors: {result.errors}"
    assert result.pdf_path is not None
    assert result.pdf_path.exists()
    assert result.pdf_path.stat().st_size > 0


@pytest.mark.integration
@pytest.mark.latex
@skip_if_no_xelatex
def test_compile_with_intentional_error(tmp_path):
    """Test that compilation properly detects and reports errors."""
    broken_tex = tmp_path / "broken.tex"
    broken_tex.write_text(
        r"""
\documentclass{article}
\begin{document}
This has an \undefinedcommand{test} that should fail.
\end{document}
"""
    )

    compile_dir = tmp_path / "compile"
    compile_dir.mkdir()

    result = compile_latex(broken_tex, compile_dir=compile_dir, num_passes=1)

    assert result.success is False
    assert len(result.errors) > 0 or "Undefined control sequence" in result.stdout


@pytest.mark.integration
@pytest.mark.latex
@skip_if_no_xelatex
def test_compile_with_artifact_cleanup(tmp_path):
    """Test artifact cleanup after compilation."""
    simple_tex = tmp_path / "simple.tex"
    simple_tex.write_text(
        r"""
\documentclass{article}
\begin{document}
Hello World
\end{document}
"""
    )

    compile_dir = tmp_path / "compile"
    compile_dir.mkdir()

    result = compile_latex(
        simple_tex, compile_dir=compile_dir, num_passes=1, keep_artifacts=False
    )

    if result.success:
        aux_file = compile_dir / "simple.aux"
        log_file = compile_dir / "simple.log"

        assert not aux_file.exists(), "Artifact .aux should be cleaned up"
        assert not log_file.exists(), "Artifact .log should be cleaned up"


@pytest.mark.integration
@pytest.mark.latex
@skip_if_no_xelatex
def test_compile_with_artifact_preservation(tmp_path):
    """Test artifact preservation when keep_artifacts=True."""
    simple_tex = tmp_path / "simple.tex"
    simple_tex.write_text(
        r"""
\documentclass{article}
\begin{document}
Hello World
\end{document}
"""
    )

    compile_dir = tmp_path / "compile"
    compile_dir.mkdir()

    result = compile_latex(
        simple_tex, compile_dir=compile_dir, num_passes=1, keep_artifacts=True
    )

    if result.success:
        log_file = compile_dir / "simple.log"
        assert log_file.exists(), "Log file should be preserved when keep_artifacts=True"


@pytest.mark.integration
@pytest.mark.latex
@skip_if_no_xelatex
def test_compile_multipass_compilation(tmp_path):
    """Test multi-pass compilation for cross-references."""
    tex_with_refs = tmp_path / "refs.tex"
    tex_with_refs.write_text(
        r"""
\documentclass{article}
\begin{document}
See section \ref{sec:test}.
\section{Test Section}
\label{sec:test}
This is a test.
\end{document}
"""
    )

    compile_dir = tmp_path / "compile"
    compile_dir.mkdir()

    result = compile_latex(tex_with_refs, compile_dir=compile_dir, num_passes=2)

    assert result.success, f"Multi-pass compilation failed: {result.errors}"
    assert result.pdf_path is not None
    assert result.pdf_path.exists()
