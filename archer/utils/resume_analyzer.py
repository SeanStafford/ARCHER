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
