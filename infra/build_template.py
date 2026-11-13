"""Genera infra/template.yaml incrustando app/app.py en el UserData (una sola fuente de verdad)."""
import pathlib
raiz = pathlib.Path(__file__).resolve().parent.parent
app = "".join("            " + l if l.strip() else "\n" for l in (raiz / "app/app.py").read_text().splitlines(True))
plantilla = (raiz / "infra/template.base.yaml").read_text().replace("__APP_PY__", app.rstrip("\n"))
(raiz / "infra/template.yaml").write_text(plantilla)
print("template.yaml generado")
