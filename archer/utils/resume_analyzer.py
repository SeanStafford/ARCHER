def analyze_keyword_frequencies(resume_dir, keyword_categories):
    tex_files = sorted(resume_dir.glob("*.tex"))
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

    return dict(keyword_total_occurrences), dict(keyword_resume_count)


def format_analysis_report( num_resumes, keyword_categories, keyword_total_occurrences, keyword_resume_count,  ):
    
    lines = []
    
    for category, keywords in keyword_categories.items():
        lines.append("=" * 100)
        lines.append(category)
        lines.append("=" * 100)
        lines.append(
            f"{'Keyword':<50} {'In N Resumes':<15} {'% Resumes':<15} {'Occurrences':<12}"
        )
        lines.append("-" * 100)

        for keyword in keywords:
            resumes_with = keyword_resume_count[keyword]
            percent_resumes = (resumes_with / num_resumes) * 100
            total_occur = keyword_total_occurrences[keyword]

            lines.append(
                f"{keyword:<50} {resumes_with:<15} "
                f"{percent_resumes:>13.1f}% {total_occur:>11}"
            )

        lines.append("")

    return "\n".join(lines)