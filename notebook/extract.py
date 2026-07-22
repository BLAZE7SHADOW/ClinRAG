
from docling.document_converter import DocumentConverter,PdfFormatOption
from docling.datamodel.base_models import   InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions,  TableFormerMode

pipeline_options = PdfPipelineOptions()

converter = DocumentConverter(format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)})  # keyword name must match the variable defined above — you renamed the variable to single underscore, so this reference needs to match


from pathlib import Path

# Get the project root (parent.parent because this file lives in notebook/,
# so one .parent lands on notebook/, the second lands on the project root)
script_dir = Path(__file__).resolve().parent.parent

# The folder all processed markdown files get written into
processed_dir = script_dir / "data" / "processed"

# Create that folder now (once, at import time) if it doesn't already exist.
# mkdir is called on processed_dir itself, not its parent -- we want
# data/processed/ to exist, not just data/
processed_dir.mkdir(parents=True, exist_ok=True)

def convert_to_markdown(pdf_path, mode="ACCURATE"):
      # pure function: takes a PDF path in, returns a markdown string out.
      # it knows nothing about where that string ends up -- that's save_markdown's job.
      pipeline_options.table_structure_options.mode = TableFormerMode[mode]  # TableFormerMode[mode] looks up the enum member whose NAME equals the string "ACCURATE" — TableFormerMode.mode would instead look for a literal attribute called "mode", which doesn't exist
      result = converter.convert(pdf_path)
      return result.document.export_to_markdown()

def save_markdown(markdown, output_path):
      # pure function: takes a markdown string + a full file path, writes it, returns nothing.
      # it knows nothing about Docling -- it would happily save any string you gave it.
      output_path.write_text(markdown)

if __name__ == "__main__":
      # only runs when this file is executed directly (python extract.py),
      # not when convert_to_markdown/save_markdown are imported elsewhere.
      for pdf_path in (script_dir / "data" / "raw").glob("*.pdf"):

        # build the output filename from the input filename:
        # metformin.pdf -> metformin.md, in data/processed/ instead of data/raw/
        output_path = processed_dir / (pdf_path.stem + ".md")

        markdown = convert_to_markdown(pdf_path)
        save_markdown(markdown, output_path)
        print(f"Saved: {output_path}")