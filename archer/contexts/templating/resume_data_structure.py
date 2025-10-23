from dataclasses import dataclass, field

from archer.contexts.templating.parser import extract_latex_fields

@dataclass
class ResumeDocument:
    
    fields = field(default_factory=dict)
    metadata = field(default_factory=dict)

    @classmethod
    def from_tex(cls, tex_path):
        content = tex_path.read_text(encoding="utf-8")
        fields = extract_latex_fields(content)

        return cls(fields=fields)

    def get_field(self, field_name):
        return self.fields.get(field_name)

