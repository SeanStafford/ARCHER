def analyze_keyword_frequencies(resume_dir, keyword_categories):
    """
    Analyze keyword frequencies across all .tex files in a directory.
    """
    tex_files = sorted(resume_dir.glob("*.tex"))

    if not tex_files:
        raise ValueError(f"No .tex files found in {resume_dir}")
        
    total_chars = 0
    all_keywords = [kw for keywords in keyword_categories.values() for kw in keywords]
    keyword_total_occurrences = {}
    keyword_resume_count = {}

    for tex_file in tex_files:
        with open(tex_file, "r") as f:
            content = f.read()
        total_chars += len(content)

        for keyword in all_keywords:
            count = content.count(keyword)
            keyword_total_occurrences[keyword] += count
            if count > 0:
                keyword_resume_count[keyword] += 1

    return (
        len(tex_files),
        total_chars,
        dict(keyword_total_occurrences),
        dict(keyword_resume_count)
    )

def format_analysis_report(
    num_resumes, total_chars, keyword_categories, keyword_total_occurrences, keyword_resume_count, resume_dir, ) -> str:
    """
    Format analysis results as a human-readable report.

    Returns:
        Formatted report string
    """
    lines = []
    lines.append(f"\nAnalyzed {num_resumes} resume files from {resume_dir}")
    lines.append(f"Total characters across all resumes: {total_chars:,}\n")

    for category, keywords in keyword_categories.items():
        lines.append("=" * 100)
        lines.append(category)
        lines.append("=" * 100)
        lines.append(
            f"{'Keyword':<50} {'In N Resumes':<15} {'% Resumes':<15} {'Occurrences':<12}"
        )
        lines.append("-" * 100)


        for keyword in keywords:
            resumes_with = keyword_resume_count.get(keyword, 0)
            percent_resumes = (resumes_with / num_resumes) * 100
            total_occur = keyword_total_occurrences.get(keyword, 0)

            display_keyword = keyword if len(keyword) <= 48 else keyword[:45] + "..."

            lines.append(
                f"{display_keyword:<50} {resumes_with:<15} "
                f"{percent_resumes:>13.1f}% {total_occur:>11}"
            )

        lines.append("")

    return "\n".join(lines)