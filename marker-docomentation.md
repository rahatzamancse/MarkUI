# Marker

Marker converts documents to markdown, JSON, and HTML quickly and accurately.

- Converts PDF, image, PPTX, DOCX, XLSX, HTML, EPUB files in all languages
- Does structured extraction, given a JSON schema (beta)
- Formats tables, forms, equations, inline math, links, references, and code blocks
- Extracts and saves images
- Removes headers/footers/other artifacts
- Extensible with your own formatting and logic
- Optionally boost accuracy with LLMs
- Works on GPU, CPU, or MPS

## Hybrid Mode

For the highest accuracy, pass the `--use_llm` flag to use an LLM alongside marker.  This will do things like merge tables across pages, handle inline math, format tables properly, and extract values from forms.  It can use any gemini or ollama model.  By default, it uses `gemini-2.0-flash`.  See [below](#llm-services) for details.

Here is a table benchmark comparing marker, gemini flash alone, and marker with use_llm:

As you can see, the use_llm mode offers higher accuracy than marker or gemini alone.

# Installation

You'll need python 3.10+ and PyTorch.  You may need to install the CPU version of torch first if you're not using a Mac or a GPU machine.  See [here](https://pytorch.org/get-started/locally/) for more details.

Install with:

```shell
pip install marker-pdf
```

If you want to use marker on documents other than PDFs, you will need to install additional dependencies with:

```shell
pip install marker-pdf[full]
```

# Usage

First, some configuration:

- Your torch device will be automatically detected, but you can override this.  For example, `TORCH_DEVICE=cuda`.
- Some PDFs, even digital ones, have bad text in them.  Set the `format_lines` flag to ensure the bad lines are fixed and formatted. You can also set `--force_ocr` to force OCR on all lines, or the `strip_existing_ocr` to keep all digital text, and strip out any existing OCR text.

## Interactive App

I've included a streamlit app that lets you interactively try marker with some basic options.  Run it with:

```shell
pip install streamlit streamlit-ace
marker_gui
```

## Convert a single file

```shell
marker_single /path/to/file.pdf
```

You can pass in PDFs or images.

Options:
- `--page_range TEXT`: Specify which pages to process. Accepts comma-separated page numbers and ranges. Example: `--page_range "0,5-10,20"` will process pages 0, 5 through 10, and page 20.
- `--output_format [markdown|json|html]`: Specify the format for the output results.
- `--output_dir PATH`: Directory where output files will be saved. Defaults to the value specified in settings.OUTPUT_DIR.
- `--paginate_output`: Paginates the output, using `\n\n{PAGE_NUMBER}` followed by `-` * 48, then `\n\n` 
- `--use_llm`: Uses an LLM to improve accuracy.  You will need to configure the LLM backend - see [below](#llm-services).
- `--format_lines`: Reformat all lines using a local OCR model (inline math, underlines, bold, etc.).  This will give very good quality math output.
- `--force_ocr`: Force OCR processing on the entire document, even for pages that might contain extractable text.
- `--strip_existing_ocr`: Remove all existing OCR text in the document and re-OCR with surya.
- `--redo_inline_math`: If you want the absolute highest quality inline math conversion, use this along with `--use_llm`.
- `--disable_image_extraction`: Don't extract images from the PDF.  If you also specify `--use_llm`, then images will be replaced with a description.
- `--debug`: Enable debug mode for additional logging and diagnostic information.
- `--processors TEXT`: Override the default processors by providing their full module paths, separated by commas. Example: `--processors "module1.processor1,module2.processor2"`
- `--config_json PATH`: Path to a JSON configuration file containing additional settings.
- `--languages TEXT`: Optionally specify which languages to use for OCR processing. Accepts a comma-separated list. Example: `--languages "en,fr,de"` for English, French, and German.
- `config --help`: List all available builders, processors, and converters, and their associated configuration.  These values can be used to build a JSON configuration file for additional tweaking of marker defaults.
- `--converter_cls`: One of `marker.converters.pdf.PdfConverter` (default) or `marker.converters.table.TableConverter`.  The `PdfConverter` will convert the whole PDF, the `TableConverter` will only extract and convert tables.
- `--llm_service`: Which llm service to use if `--use_llm` is passed.  This defaults to `marker.services.gemini.GoogleGeminiService`.
- `--help`: see all of the flags that can be passed into marker.  (it supports many more options then are listed above)

The list of supported languages for surya OCR is [here](https://github.com/VikParuchuri/surya/blob/master/surya/recognition/languages.py).  If you don't need OCR, marker can work with any language.

## Convert multiple files

```shell
marker /path/to/input/folder --workers 4
```

- `marker` supports all the same options from `marker_single` above.
- `--workers` is the number of conversion workers to run simultaneously.  This is set to 5 by default, but you can increase it to increase throughput, at the cost of more CPU/GPU usage.  Marker will use 5GB of VRAM per worker at the peak, and 3.5GB average.

## Convert multiple files on multiple GPUs

```shell
NUM_DEVICES=4 NUM_WORKERS=15 marker_chunk_convert ../pdf_in ../md_out
```

- `NUM_DEVICES` is the number of GPUs to use.  Should be `2` or greater.
- `NUM_WORKERS` is the number of parallel processes to run on each GPU.

## Use from python

See the `PdfConverter` class at `marker/converters/pdf.py` function for additional arguments that can be passed.

```python
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.output import text_from_rendered

converter = PdfConverter(
    artifact_dict=create_model_dict(),
)
rendered = converter("FILEPATH")
text, _, images = text_from_rendered(rendered)
```

`rendered` will be a pydantic basemodel with different properties depending on the output type requested.  With markdown output (default), you'll have the properties `markdown`, `metadata`, and `images`.  For json output, you'll have `children`, `block_type`, and `metadata`.

### Custom configuration

You can pass configuration using the `ConfigParser`.  To see all available options, do `marker_single --help`.

```python
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.config.parser import ConfigParser

config = {
    "output_format": "json",
    "ADDITIONAL_KEY": "VALUE"
}
config_parser = ConfigParser(config)

converter = PdfConverter(
    config=config_parser.generate_config_dict(),
    artifact_dict=create_model_dict(),
    processor_list=config_parser.get_processors(),
    renderer=config_parser.get_renderer(),
    llm_service=config_parser.get_llm_service()
)
rendered = converter("FILEPATH")
```

### Extract blocks

Each document consists of one or more pages.  Pages contain blocks, which can themselves contain other blocks.  It's possible to programmatically manipulate these blocks.  

Here's an example of extracting all forms from a document:

```python
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.schema import BlockTypes

converter = PdfConverter(
    artifact_dict=create_model_dict(),
)
document = converter.build_document("FILEPATH")
forms = document.contained_blocks((BlockTypes.Form,))
```

Look at the processors for more examples of extracting and manipulating blocks.

## Other converters

You can also use other converters that define different conversion pipelines:

### Extract tables

The `TableConverter` will only convert and extract tables:

```python
from marker.converters.table import TableConverter
from marker.models import create_model_dict
from marker.output import text_from_rendered

converter = TableConverter(
    artifact_dict=create_model_dict(),
)
rendered = converter("FILEPATH")
text, _, images = text_from_rendered(rendered)
```

This takes all the same configuration as the PdfConverter.  You can specify the configuration `force_layout_block=Table` to avoid layout detection and instead assume every page is a table.  Set `output_format=json` to also get cell bounding boxes.

You can also run this via the CLI with 
```shell
marker_single FILENAME --use_llm --force_layout_block Table --converter_cls marker.converters.table.TableConverter --output_format json
```

### OCR Only

If you only want to run OCR, you can also do that through the `OCRConverter`.  Set `--keep_chars` to keep individual characters and bounding boxes.  You can also set `--force_ocr` and `--format_lines` with this converter.

```python
from marker.converters.ocr import OCRConverter
from marker.models import create_model_dict

converter = OCRConverter(
    artifact_dict=create_model_dict(),
)
rendered = converter("FILEPATH")
```

This takes all the same configuration as the PdfConverter.

You can also run this via the CLI with 
```shell
marker_single FILENAME --converter_cls marker.converters.ocr.OCRConverter
```

### Structured Extraction (beta)

You can run structured extraction via the `ExtractionConverter`.  This requires an llm service to be setup first (see [here](#llm-services) for details).  You'll get a JSON output with the extracted values.

```python
from marker.converters.extraction import ExtractionConverter
from marker.models import create_model_dict
from marker.config.parser import ConfigParser
from pydantic import BaseModel

class Links(BaseModel):
    links: list[str]
    
schema = Links.model_json_schema()
config_parser = ConfigParser({
    "page_schema": schema
})

converter = ExtractionConverter(
    artifact_dict=create_model_dict(),
    config=config_parser.generate_config_dict(),
    llm_service=config_parser.get_llm_service(),
)
rendered = converter("FILEPATH")
```

# Output Formats

## Markdown

Markdown output will include:

- image links (images will be saved in the same folder)
- formatted tables
- embedded LaTeX equations (fenced with `$$`)
- Code is fenced with triple backticks
- Superscripts for footnotes

## HTML

HTML output is similar to markdown output:

- Images are included via `img` tags
- equations are fenced with `<math>` tags
- code is in `pre` tags

## JSON

JSON output will be organized in a tree-like structure, with the leaf nodes being blocks.  Examples of leaf nodes are a single list item, a paragraph of text, or an image.

The output will be a list, with each list item representing a page.  Each page is considered a block in the internal marker schema.  There are different types of blocks to represent different elements.  

Pages have the keys:

- `id` - unique id for the block.
- `block_type` - the type of block. The possible block types can be seen in `marker/schema/__init__.py`.  As of this writing, they are ["Line", "Span", "FigureGroup", "TableGroup", "ListGroup", "PictureGroup", "Page", "Caption", "Code", "Figure", "Footnote", "Form", "Equation", "Handwriting", "TextInlineMath", "ListItem", "PageFooter", "PageHeader", "Picture", "SectionHeader", "Table", "Text", "TableOfContents", "Document"]
- `html` - the HTML for the page.  Note that this will have recursive references to children.  The `content-ref` tags must be replaced with the child content if you want the full html.  You can see an example of this at `marker/output.py:json_to_html`.  That function will take in a single block from the json output, and turn it into HTML.
- `polygon` - the 4-corner polygon of the page, in (x1,y1), (x2,y2), (x3, y3), (x4, y4) format.  (x1,y1) is the top left, and coordinates go clockwise.
- `children` - the child blocks.

The child blocks have two additional keys:

- `section_hierarchy` - indicates the sections that the block is part of.  `1` indicates an h1 tag, `2` an h2, and so on.
- `images` - base64 encoded images.  The key will be the block id, and the data will be the encoded image.

Note that child blocks of pages can have their own children as well (a tree structure).

```json
{
      "id": "/page/10/Page/366",
      "block_type": "Page",
      "html": "<content-ref src='/page/10/SectionHeader/0'></content-ref><content-ref src='/page/10/SectionHeader/1'></content-ref><content-ref src='/page/10/Text/2'></content-ref><content-ref src='/page/10/Text/3'></content-ref><content-ref src='/page/10/Figure/4'></content-ref><content-ref src='/page/10/SectionHeader/5'></content-ref><content-ref src='/page/10/SectionHeader/6'></content-ref><content-ref src='/page/10/TextInlineMath/7'></content-ref><content-ref src='/page/10/TextInlineMath/8'></content-ref><content-ref src='/page/10/Table/9'></content-ref><content-ref src='/page/10/SectionHeader/10'></content-ref><content-ref src='/page/10/Text/11'></content-ref>",
      "polygon": [[0.0, 0.0], [612.0, 0.0], [612.0, 792.0], [0.0, 792.0]],
      "children": [
        {
          "id": "/page/10/SectionHeader/0",
          "block_type": "SectionHeader",
          "html": "<h1>Supplementary Material for <i>Subspace Adversarial Training</i> </h1>",
          "polygon": [
            [217.845703125, 80.630859375], [374.73046875, 80.630859375],
            [374.73046875, 107.0],
            [217.845703125, 107.0]
          ],
          "children": null,
          "section_hierarchy": {
            "1": "/page/10/SectionHeader/1"
          },
          "images": {}
        },
        ...
        ]
    }


```

## Metadata

All output formats will return a metadata dictionary, with the following fields:

```json
{
    "table_of_contents": [
      {
        "title": "Introduction",
        "heading_level": 1,
        "page_id": 0,
        "polygon": [...]
      }
    ], // computed PDF table of contents
    "page_stats": [
      {
        "page_id":  0, 
        "text_extraction_method": "pdftext",
        "block_counts": [("Span", 200), ...]
      },
      ...
    ]
}
```

# LLM Services

When running with the `--use_llm` flag, you have a choice of services you can use:

- `Gemini` - this will use the Gemini developer API by default.  You'll need to pass `--gemini_api_key` to configuration.
- `Google Vertex` - this will use vertex, which can be more reliable.  You'll need to pass `--vertex_project_id`.  To use it, set `--llm_service=marker.services.vertex.GoogleVertexService`.
- `Ollama` - this will use local models.  You can configure `--ollama_base_url` and `--ollama_model`. To use it, set `--llm_service=marker.services.ollama.OllamaService`.
- `Claude` - this will use the anthropic API.  You can configure `--claude_api_key`, and `--claude_model_name`.  To use it, set `--llm_service=marker.services.claude.ClaudeService`.
- `OpenAI` - this supports any openai-like endpoint. You can configure `--openai_api_key`, `--openai_model`, and `--openai_base_url`. To use it, set `--llm_service=marker.services.openai.OpenAIService`.

These services may have additional optional configuration as well - you can see it by viewing the classes.

# Internals

Marker is easy to extend.  The core units of marker are:

- `Providers`, at `marker/providers`.  These provide information from a source file, like a PDF.
- `Builders`, at `marker/builders`.  These generate the initial document blocks and fill in text, using info from the providers.
- `Processors`, at `marker/processors`.  These process specific blocks, for example the table formatter is a processor.
- `Renderers`, at `marker/renderers`. These use the blocks to render output.
- `Schema`, at `marker/schema`.  The classes for all the block types.
- `Converters`, at `marker/converters`.  They run the whole end to end pipeline.

To customize processing behavior, override the `processors`.  To add new output formats, write a new `renderer`.  For additional input formats, write a new `provider.`

Processors and renderers can be directly passed into the base `PDFConverter`, so you can specify your own custom processing easily.

## API server

There is a very simple API server you can run like this:

```shell
pip install -U uvicorn fastapi python-multipart
marker_server --port 8001
```

This will start a fastapi server that you can access at `localhost:8001`.  You can go to `localhost:8001/docs` to see the endpoint options.

You can send requests like this:

```
import requests
import json

post_data = {
    'filepath': 'FILEPATH',
    # Add other params here
}

requests.post("http://localhost:8001/marker", data=json.dumps(post_data)).json()
```

Note that this is not a very robust API, and is only intended for small-scale use.  If you want to use this server, but want a more robust conversion option, you can use the hosted [Datalab API](https://www.datalab.to/plans).

# Troubleshooting

There are some settings that you may find useful if things aren't working the way you expect:

- If you have issues with accuracy, try setting `--use_llm` to use an LLM to improve quality.  You must set `GOOGLE_API_KEY` to a Gemini API key for this to work.
- Make sure to set `force_ocr` if you see garbled text - this will re-OCR the document.
- `TORCH_DEVICE` - set this to force marker to use a given torch device for inference.
- If you're getting out of memory errors, decrease worker count.  You can also try splitting up long PDFs into multiple files.

## Debugging

Pass the `debug` option to activate debug mode.  This will save images of each page with detected layout and text, as well as output a json file with additional bounding box information.

# Benchmarks

## Overall PDF Conversion

We created a [benchmark set](https://huggingface.co/datasets/datalab-to/marker_benchmark) by extracting single PDF pages from common crawl.  We scored based on a heuristic that aligns text with ground truth text segments, and an LLM as a judge scoring method.

| Method     | Avg Time | Heuristic Score | LLM Score |
|------------|----------|-----------------|-----------|
| marker     | 2.83837  | 95.6709         | 4.23916   |
| llamaparse | 23.348   | 84.2442         | 3.97619   |
| mathpix    | 6.36223  | 86.4281         | 4.15626   |
| docling    | 3.69949  | 86.7073         | 3.70429   |

Benchmarks were run on an H100 for markjer and docling - llamaparse and mathpix used their cloud services.  We can also look at it by document type:

<img src="data/images/per_doc.png" width="1000px"/>

| Document Type        | Marker heuristic | Marker LLM | Llamaparse Heuristic | Llamaparse LLM | Mathpix Heuristic | Mathpix LLM | Docling Heuristic | Docling LLM |
|----------------------|------------------|------------|----------------------|----------------|-------------------|-------------|-------------------|-------------|
| Scientific paper     | 96.6737          | 4.34899    | 87.1651              | 3.96421        | 91.2267           | 4.46861     | 92.135            | 3.72422     |
| Book page            | 97.1846          | 4.16168    | 90.9532              | 4.07186        | 93.8886           | 4.35329     | 90.0556           | 3.64671     |
| Other                | 95.1632          | 4.25076    | 81.1385              | 4.01835        | 79.6231           | 4.00306     | 83.8223           | 3.76147     |
| Form                 | 88.0147          | 3.84663    | 66.3081              | 3.68712        | 64.7512           | 3.33129     | 68.3857           | 3.40491     |
| Presentation         | 95.1562          | 4.13669    | 81.2261              | 4              | 83.6737           | 3.95683     | 84.8405           | 3.86331     |
| Financial document   | 95.3697          | 4.39106    | 82.5812              | 4.16111        | 81.3115           | 4.05556     | 86.3882           | 3.8         |
| Letter               | 98.4021          | 4.5        | 93.4477              | 4.28125        | 96.0383           | 4.45312     | 92.0952           | 4.09375     |
| Engineering document | 93.9244          | 4.04412    | 77.4854              | 3.72059        | 80.3319           | 3.88235     | 79.6807           | 3.42647     |
| Legal document       | 96.689           | 4.27759    | 86.9769              | 3.87584        | 91.601            | 4.20805     | 87.8383           | 3.65552     |
| Newspaper page       | 98.8733          | 4.25806    | 84.7492              | 3.90323        | 96.9963           | 4.45161     | 92.6496           | 3.51613     |
| Magazine page        | 98.2145          | 4.38776    | 87.2902              | 3.97959        | 93.5934           | 4.16327     | 93.0892           | 4.02041     |

## Throughput

We benchmarked throughput using a [single long PDF](https://www.greenteapress.com/thinkpython/thinkpython.pdf).

| Method  | Time per page | Time per document | VRAM used |
|---------|---------------|-------------------|---------- |
| marker  | 0.18          | 43.42             |  3.17GB   |

The projected throughput is 122 pages per second on an H100 - we can run 22 individual processes given the VRAM used.

## Table Conversion

Marker can extract tables from PDFs using `marker.converters.table.TableConverter`. The table extraction performance is measured by comparing the extracted HTML representation of tables against the original HTML representations using the test split of [FinTabNet](https://developer.ibm.com/exchanges/data/all/fintabnet/). The HTML representations are compared using a tree edit distance based metric to judge both structure and content. Marker detects and identifies the structure of all tables in a PDF page and achieves these scores:

| Method           | Avg score | Total tables |
|------------------|-----------|--------------|
| marker           | 0.816     | 99           |
| marker w/use_llm | 0.907     | 99           |
| gemini           | 0.829     | 99           |

The `--use_llm` flag can significantly improve table recognition performance, as you can see.

We filter out tables that we cannot align with the ground truth, since fintabnet and our layout model have slightly different detection methods (this results in some tables being split/merged).

## Running your own benchmarks

You can benchmark the performance of marker on your machine. Install marker manually with:

```shell
git clone https://github.com/VikParuchuri/marker.git
poetry install
```

### Overall PDF Conversion

Download the benchmark data [here](https://drive.google.com/file/d/1ZSeWDo2g1y0BRLT7KnbmytV2bjWARWba/view?usp=sharing) and unzip. Then run the overall benchmark like this:

```shell
python benchmarks/overall.py --methods marker --scores heuristic,llm
```

Options:

- `--use_llm` use an llm to improve the marker results.
- `--max_rows` how many rows to process for the benchmark.
- `--methods` can be `llamaparse`, `mathpix`, `docling`, `marker`.  Comma separated.
- `--scores` which scoring functions to use, can be `llm`, `heuristic`.  Comma separated.

### Table Conversion
The processed FinTabNet dataset is hosted [here](https://huggingface.co/datasets/datalab-to/fintabnet-test) and is automatically downloaded. Run the benchmark with:

```shell
python benchmarks/table/table.py --max_rows 100
```

Options:

- `--use_llm` uses an llm with marker to improve accuracy.
- `--use_gemini` also benchmarks gemini 2.0 flash.

# How it works

Marker is a pipeline of deep learning models:

- Extract text, OCR if necessary (heuristics, [surya](https://github.com/VikParuchuri/surya))
- Detect page layout and find reading order ([surya](https://github.com/VikParuchuri/surya))
- Clean and format each block (heuristics, [texify](https://github.com/VikParuchuri/texify), [surya](https://github.com/VikParuchuri/surya))
- Optionally use an LLM to improve quality
- Combine blocks and postprocess complete text

It only uses models where necessary, which improves speed and accuracy.

# Limitations

PDF is a tricky format, so marker will not always work perfectly.  Here are some known limitations that are on the roadmap to address:

- Very complex layouts, with nested tables and forms, may not work
- Forms may not be rendered well

Note: Passing the `--use_llm` and `--format_lines` flags will mostly solve these issues.


# `--help` outputs

### `marker_single --help`

```
Usage: marker_single [OPTIONS] FPATH

  Convert a single PDF to markdown.

Options:
  --llm_service TEXT              LLM service to use - should be full import
                                  path, like
                                  marker.services.gemini.GoogleGeminiService
  --converter_cls TEXT            Converter class to use.  Defaults to PDF
                                  converter.
  --page_range TEXT               Page range to convert, specify comma
                                  separated page numbers or ranges.  Example:
                                  0,5-10,20
  --disable_image_extraction      Disable image extraction.
  --disable_multiprocessing       Disable multiprocessing.
  --config_json TEXT              Path to JSON file with additional
                                  configuration.
  --processors TEXT               Comma separated list of processors to use.
                                  Must use full module path.
  --output_format [markdown|json|html]
                                  Format to output results in.
  -d, --debug                     Enable debug mode.
  --output_dir PATH               Directory to save output.
  --lowres_image_dpi INTEGER      DPI setting for low-resolution page images
                                  used for Layout and Line Detection. Default
                                  is 96. (Applies to: DocumentBuilder)
  --highres_image_dpi INTEGER     DPI setting for high-resolution page images
                                  used for OCR. Default is 192. (Applies to:
                                  DocumentBuilder)
  --disable_ocr                   Disable OCR processing. Default is False.
                                  (Applies to: DocumentBuilder)
  --layout_batch_size OPTIONAL    The batch size to use for the layout model.
                                  Default is None, which will use the default
                                  batch size for the model. (Applies to:
                                  LayoutBuilder, LLMLayoutBuilder)
  --force_layout_block TEXT       Skip layout and force every page to be
                                  treated as a specific block type. Default is
                                  None. (Applies to: LayoutBuilder,
                                  LLMLayoutBuilder)
  --disable_tqdm                  Disable tqdm progress bars. Default is
                                  False. (Applies to: LayoutBuilder,
                                  LineBuilder, OcrBuilder, LLMLayoutBuilder,
                                  EquationProcessor,
                                  LLMComplexRegionProcessor,
                                  LLMEquationProcessor, LLMFormProcessor,
                                  LLMHandwritingProcessor,
                                  LLMImageDescriptionProcessor,
                                  LLMMathBlockProcessor,
                                  LLMSimpleBlockMetaProcessor,
                                  LLMTableProcessor, LLMTableMergeProcessor,
                                  TableProcessor, PageExtractor)
  --detection_batch_size OPTIONAL
                                  The batch size to use for the detection
                                  model. Default is None, which will use the
                                  default batch size for the model. (Applies
                                  to: LineBuilder, TableProcessor)
  --ocr_error_batch_size OPTIONAL
                                  The batch size to use for the ocr error
                                  detection model. Default is None, which will
                                  use the default batch size for the model.
                                  (Applies to: LineBuilder)
  --enable_table_ocr              Whether to skip OCR on tables.  The
                                  TableProcessor will re-OCR them.  Only
                                  enable if the TableProcessor is not running.
                                  Default is False. (Applies to: LineBuilder)
  --format_lines                  Enable good provider lines to be checked and
                                  fixed by the OCR model Default is False.
                                  (Applies to: LineBuilder, TableProcessor)
  --layout_coverage_min_lines INTEGER
                                  The minimum number of PdfProvider lines that
                                  must be covered by the layout model to
                                  consider the lines from the PdfProvider
                                  valid. Default is 1. (Applies to:
                                  LineBuilder)
  --layout_coverage_threshold FLOAT
                                  The minimum coverage ratio required for the
                                  layout model to consider the lines from the
                                  PdfProvider valid. Default is 0.25. (Applies
                                  to: LineBuilder)
  --min_document_ocr_threshold FLOAT
                                  If less pages than this threshold are good,
                                  OCR will happen in the document.  Otherwise
                                  it will not. Default is 0.85. (Applies to:
                                  LineBuilder)
  --provider_line_detected_line_min_overlap_pct FLOAT
                                  The percentage of a provider line that has
                                  to be covered by a detected line Default is
                                  0.1. (Applies to: LineBuilder)
  --line_vertical_merge_threshold INTEGER
                                  The maximum pixel distance between y1s for
                                  two lines to be merged Default is 8.
                                  (Applies to: LineBuilder)
  --keep_chars                    Keep individual characters. Default is
                                  False. (Applies to: LineBuilder, OcrBuilder)
  --recognition_batch_size OPTIONAL
                                  The batch size to use for the recognition
                                  model. Default is None, which will use the
                                  default batch size for the model. (Applies
                                  to: OcrBuilder, TableProcessor)
  --ocr_task_name TEXT            The OCR mode to use, see surya for details.
                                  Set to 'ocr_without_boxes' for potentially
                                  better performance, at the expense of
                                  formatting. Default is ocr_with_boxes.
                                  (Applies to: OcrBuilder)
  --disable_ocr_math              Disable inline math recognition in OCR
                                  Default is False. (Applies to: OcrBuilder)
  --google_api_key TEXT           The Google API key to use for the Gemini
                                  model. Default is . (Applies to:
                                  LLMLayoutBuilder)
  --confidence_threshold FLOAT    The confidence threshold to use for
                                  relabeling (anything below is relabeled).
                                  Default is 0.7. (Applies to:
                                  LLMLayoutBuilder)
  --picture_height_threshold FLOAT
                                  The height threshold for pictures that may
                                  actually be complex regions. (anything above
                                  this ratio against the page is relabeled)
                                  Default is 0.8. (Applies to:
                                  LLMLayoutBuilder)
  --model_name TEXT               The name of the Gemini model to use. Default
                                  is gemini-2.0-flash. (Applies to:
                                  LLMLayoutBuilder)
  --max_concurrency INTEGER       The maximum number of concurrent requests to
                                  make to the Gemini model. Default is 3.
                                  (Applies to: LLMLayoutBuilder,
                                  LLMComplexRegionProcessor,
                                  LLMEquationProcessor, LLMFormProcessor,
                                  LLMHandwritingProcessor,
                                  LLMImageDescriptionProcessor,
                                  LLMMathBlockProcessor,
                                  LLMSimpleBlockMetaProcessor,
                                  LLMTableProcessor, LLMTableMergeProcessor,
                                  PageExtractor)
  --topk_relabelling_prompt TEXT  The prompt to use for relabelling blocks.
                                  Default is a string containing the Gemini
                                  relabelling prompt. (Applies to:
                                  LLMLayoutBuilder)
  --complex_relabeling_prompt TEXT
                                  The prompt to use for complex relabelling
                                  blocks. Default is a string containing the
                                  complex relabelling prompt. (Applies to:
                                  LLMLayoutBuilder)
  --gap_threshold FLOAT           The minimum gap between blocks to consider
                                  them part of the same group. Default is
                                  0.05. (Applies to: StructureBuilder)
  --list_gap_threshold FLOAT      The minimum gap between list items to
                                  consider them part of the same group.
                                  Default is 0.1. (Applies to:
                                  StructureBuilder)
  --min_x_indent FLOAT            The minimum horizontal indentation required
                                  to consider a block as part of a blockquote.
                                  Expressed as a percentage of the block
                                  width. Default is 0.1. (Applies to:
                                  BlockquoteProcessor, ListProcessor)
  --x_start_tolerance FLOAT       The maximum allowable difference between the
                                  starting x-coordinates of consecutive blocks
                                  to consider them aligned. Expressed as a
                                  percentage of the block width. Default is
                                  0.01. (Applies to: BlockquoteProcessor)
  --x_end_tolerance FLOAT         The maximum allowable difference between the
                                  ending x-coordinates of consecutive blocks
                                  to consider them aligned. Expressed as a
                                  percentage of the block width. Default is
                                  0.01. (Applies to: BlockquoteProcessor)
  --debug_data_folder TEXT        The folder to dump debug data to. Default is
                                  debug_data. (Applies to: DebugProcessor)
  --debug_layout_images           Whether to dump layout debug images. Default
                                  is False. (Applies to: DebugProcessor)
  --debug_pdf_images              Whether to dump PDF debug images. Default is
                                  False. (Applies to: DebugProcessor)
  --debug_json                    Whether to dump block debug data. Default is
                                  False. (Applies to: DebugProcessor)
  --model_max_length INTEGER      The maximum number of tokens to allow for
                                  the Recognition model. Default is 1024.
                                  (Applies to: EquationProcessor)
  --equation_batch_size OPTIONAL  The batch size to use for the recognition
                                  model while processing equations. Default is
                                  None, which will use the default batch size
                                  for the model. (Applies to:
                                  EquationProcessor)
  --common_element_threshold FLOAT
                                  The minimum ratio of pages a text block must
                                  appear on to be considered a common element.
                                  Blocks that meet or exceed this threshold
                                  are marked as common elements. Default is
                                  0.2. (Applies to: IgnoreTextProcessor)
  --common_element_min_blocks INTEGER
                                  The minimum number of occurrences of a text
                                  block within a document to consider it a
                                  common element. This ensures that rare
                                  blocks are not mistakenly flagged. Default
                                  is 3. (Applies to: IgnoreTextProcessor)
  --max_streak INTEGER            The maximum number of consecutive
                                  occurrences of a text block allowed before
                                  it is classified as a common element. Helps
                                  to identify patterns like repeated headers
                                  or footers. Default is 3. (Applies to:
                                  IgnoreTextProcessor)
  --text_match_threshold INTEGER  The minimum fuzzy match score (0-100)
                                  required to classify a text block as similar
                                  to a common element. Higher values enforce
                                  stricter matching. Default is 90. (Applies
                                  to: IgnoreTextProcessor)
  --min_merge_pct FLOAT           The minimum percentage of intersection area
                                  to consider merging. Default is 0.015.
                                  (Applies to: LineMergeProcessor)
  --block_expand_threshold FLOAT  The percentage of the block width to expand
                                  the bounding box. Default is 0.05. (Applies
                                  to: LineMergeProcessor)
  --min_merge_ydist FLOAT         The minimum y distance between lines to
                                  consider merging. Default is 5. (Applies to:
                                  LineMergeProcessor)
  --intersection_pct_threshold FLOAT
                                  The total amount of intersection area
                                  concentrated in the max intersection block.
                                  Default is 0.5. (Applies to:
                                  LineMergeProcessor)
  --vertical_overlap_pct_threshold FLOAT
                                  The minimum percentage of vertical overlap
                                  to consider merging. Default is 0.8.
                                  (Applies to: LineMergeProcessor)
  --use_llm                       Whether to use LLMs to improve accuracy.
                                  Default is False. (Applies to:
                                  LineMergeProcessor,
                                  LLMComplexRegionProcessor,
                                  LLMEquationProcessor, LLMFormProcessor,
                                  LLMHandwritingProcessor,
                                  LLMImageDescriptionProcessor,
                                  LLMMathBlockProcessor,
                                  LLMSimpleBlockMetaProcessor,
                                  LLMTableProcessor, LLMTableMergeProcessor,
                                  ExtractionConverter, PdfConverter,
                                  OCRConverter, TableConverter)
  --strip_numbers_threshold FLOAT
                                  The fraction of lines or tokens in a block
                                  that must be numeric to consider them as
                                  line numbers. Default is 0.6. (Applies to:
                                  LineNumbersProcessor)
  --min_lines_in_block INTEGER    The minimum number of lines required in a
                                  block for it to be considered during
                                  processing. Ensures that small blocks are
                                  ignored as they are unlikely to contain
                                  meaningful line numbers. Default is 4.
                                  (Applies to: LineNumbersProcessor)
  --min_line_length INTEGER       The minimum length of a line (in characters)
                                  to consider it significant when checking for
                                  numeric prefixes or suffixes. Prevents false
                                  positives for short lines. Default is 10.
                                  (Applies to: LineNumbersProcessor)
  --min_line_number_span_ratio FLOAT
                                  The minimum ratio of detected line number
                                  spans to total lines required to treat them
                                  as line numbers. Default is 0.6. (Applies
                                  to: LineNumbersProcessor)
  --image_expansion_ratio FLOAT   The ratio to expand the image by when
                                  cropping. Default is 0.01. (Applies to:
                                  LLMComplexRegionProcessor,
                                  LLMEquationProcessor, LLMFormProcessor,
                                  LLMHandwritingProcessor,
                                  LLMImageDescriptionProcessor,
                                  LLMMathBlockProcessor,
                                  LLMSimpleBlockMetaProcessor,
                                  LLMTableProcessor, LLMTableMergeProcessor)
  --min_equation_height FLOAT     The minimum ratio between equation height
                                  and page height to consider for processing.
                                  Default is 0.06. (Applies to:
                                  LLMEquationProcessor)
  --redo_inline_math              Whether to redo inline math blocks. Default
                                  is False. (Applies to: LLMEquationProcessor,
                                  LLMMathBlockProcessor)
  --equation_latex_prompt TEXT    The prompt to use for generating LaTeX from
                                  equations. Default is a string containing
                                  the Gemini prompt. (Applies to:
                                  LLMEquationProcessor)
  --handwriting_generation_prompt TEXT
                                  The prompt to use for OCRing handwriting.
                                  Default is a string containing the Gemini
                                  prompt. (Applies to:
                                  LLMHandwritingProcessor)
  --extract_images BOOLEAN        Extract images from the document. Default is
                                  True. (Applies to:
                                  LLMImageDescriptionProcessor,
                                  ExtractionRenderer, HTMLRenderer,
                                  JSONRenderer, MarkdownRenderer,
                                  OCRJSONRenderer)
  --image_description_prompt TEXT
                                  The prompt to use for generating image
                                  descriptions. Default is a string containing
                                  the Gemini prompt. (Applies to:
                                  LLMImageDescriptionProcessor)
  --inlinemath_min_ratio FLOAT    If more than this ratio of blocks are
                                  inlinemath blocks, assume everything has
                                  math. Default is 0.4. (Applies to:
                                  LLMMathBlockProcessor)
  --max_rows_per_batch INTEGER    If the table has more rows than this, chunk
                                  the table. (LLMs can be inaccurate with a
                                  lot of rows) Default is 60. (Applies to:
                                  LLMTableProcessor)
  --max_table_rows INTEGER        The maximum number of rows in a table to
                                  process with the LLM processor.  Beyond this
                                  will be skipped. Default is 175. (Applies
                                  to: LLMTableProcessor)
  --table_image_expansion_ratio FLOAT
                                  The ratio to expand the image by when
                                  cropping. Default is 0. (Applies to:
                                  LLMTableProcessor)
  --rotation_max_wh_ratio FLOAT   The maximum width/height ratio for table
                                  cells for a table to be considered rotated.
                                  Default is 0.6. (Applies to:
                                  LLMTableProcessor)
  --table_rewriting_prompt TEXT   The prompt to use for rewriting text.
                                  Default is a string containing the Gemini
                                  rewriting prompt. (Applies to:
                                  LLMTableProcessor)
  --table_height_threshold FLOAT  The minimum height ratio relative to the
                                  page for the first table in a pair to be
                                  considered for merging. Default is 0.6.
                                  (Applies to: LLMTableMergeProcessor)
  --table_start_threshold FLOAT   The maximum percentage down the page the
                                  second table can start to be considered for
                                  merging. Default is 0.2. (Applies to:
                                  LLMTableMergeProcessor)
  --vertical_table_height_threshold FLOAT
                                  The height tolerance for 2 adjacent tables
                                  to be merged into one. Default is 0.25.
                                  (Applies to: LLMTableMergeProcessor)
  --vertical_table_distance_threshold INTEGER
                                  The maximum distance between table edges for
                                  adjacency. Default is 20. (Applies to:
                                  LLMTableMergeProcessor)
  --horizontal_table_width_threshold FLOAT
                                  The width tolerance for 2 adjacent tables to
                                  be merged into one. Default is 0.25.
                                  (Applies to: LLMTableMergeProcessor)
  --horizontal_table_distance_threshold INTEGER
                                  The maximum distance between table edges for
                                  adjacency. Default is 10. (Applies to:
                                  LLMTableMergeProcessor)
  --column_gap_threshold INTEGER  The maximum gap between columns to merge
                                  tables Default is 50. (Applies to:
                                  LLMTableMergeProcessor)
  --table_merge_prompt TEXT       The prompt to use for rewriting text.
                                  Default is a string containing the Gemini
                                  rewriting prompt. (Applies to:
                                  LLMTableMergeProcessor)
  --level_count INTEGER           The number of levels to use for headings.
                                  Default is 4. (Applies to:
                                  SectionHeaderProcessor)
  --merge_threshold FLOAT         The minimum gap between headings to consider
                                  them part of the same group. Default is
                                  0.25. (Applies to: SectionHeaderProcessor)
  --default_level INTEGER         The default heading level to use if no
                                  heading level is detected. Default is 2.
                                  (Applies to: SectionHeaderProcessor)
  --height_tolerance FLOAT        The minimum height of a heading to consider
                                  it a heading. Default is 0.99. (Applies to:
                                  SectionHeaderProcessor)
  --detect_boxes                  Whether to detect boxes for the table
                                  recognition model. Default is False.
                                  (Applies to: TableProcessor)
  --table_rec_batch_size INTEGER  The batch size to use for the table
                                  recognition model. Default is None, which
                                  will use the default batch size for the
                                  model. (Applies to: TableProcessor)
  --row_split_threshold FLOAT     The percentage of rows that need to be split
                                  across the table before row splitting is
                                  active. Default is 0.5. (Applies to:
                                  TableProcessor)
  --pdftext_workers INTEGER       The number of workers to use for pdftext.
                                  Default is 1. (Applies to: TableProcessor,
                                  DocumentProvider, PdfProvider, EpubProvider,
                                  HTMLProvider, PowerPointProvider,
                                  SpreadSheetProvider)
  --column_gap_ratio FLOAT        The minimum ratio of the page width to the
                                  column gap to consider a column break.
                                  Default is 0.02. (Applies to: TextProcessor)
  --pattern TEXT                  Default is {\d+\}-{48}\n\n. (Applies to:
                                  ExtractionConverter)
  --flatten_pdf BOOLEAN           Whether to flatten the PDF structure.
                                  Default is True. (Applies to:
                                  DocumentProvider, PdfProvider, EpubProvider,
                                  HTMLProvider, PowerPointProvider,
                                  SpreadSheetProvider)
  --force_ocr                     Whether to force OCR on the whole document.
                                  Default is False. (Applies to:
                                  DocumentProvider, PdfProvider, EpubProvider,
                                  HTMLProvider, PowerPointProvider,
                                  SpreadSheetProvider)
  --ocr_space_threshold FLOAT     The minimum ratio of spaces to non-spaces to
                                  detect bad text. Default is 0.7. (Applies
                                  to: DocumentProvider, PdfProvider,
                                  EpubProvider, HTMLProvider,
                                  PowerPointProvider, SpreadSheetProvider)
  --ocr_newline_threshold FLOAT   The minimum ratio of newlines to non-
                                  newlines to detect bad text. Default is 0.6.
                                  (Applies to: DocumentProvider, PdfProvider,
                                  EpubProvider, HTMLProvider,
                                  PowerPointProvider, SpreadSheetProvider)
  --ocr_alphanum_threshold FLOAT  The minimum ratio of alphanumeric characters
                                  to non-alphanumeric characters to consider
                                  an alphanumeric character. Default is 0.3.
                                  (Applies to: DocumentProvider, PdfProvider,
                                  EpubProvider, HTMLProvider,
                                  PowerPointProvider, SpreadSheetProvider)
  --image_threshold FLOAT         The minimum coverage ratio of the image to
                                  the page to consider skipping the page.
                                  Default is 0.65. (Applies to:
                                  DocumentProvider, PdfProvider, EpubProvider,
                                  HTMLProvider, PowerPointProvider,
                                  SpreadSheetProvider)
  --strip_existing_ocr            Whether to strip existing OCR text from the
                                  PDF. Default is False. (Applies to:
                                  DocumentProvider, PdfProvider, EpubProvider,
                                  HTMLProvider, PowerPointProvider,
                                  SpreadSheetProvider)
  --disable_links                 Whether to disable links. Default is False.
                                  (Applies to: DocumentProvider, PdfProvider,
                                  EpubProvider, HTMLProvider,
                                  PowerPointProvider, SpreadSheetProvider)
  --image_count INTEGER           Default is 1. (Applies to: ImageProvider)
  --include_slide_number          Default is False. (Applies to:
                                  PowerPointProvider)
  --paginate_output               Whether to paginate the output. Default is
                                  False. (Applies to: HTMLRenderer,
                                  MarkdownRenderer)
  --page_separator TEXT           The separator to use between pages. Default
                                  is '-' * 48. (Applies to: MarkdownRenderer)
  --timeout INTEGER               The timeout to use for the service. Default
                                  is 30. (Applies to: ClaudeService,
                                  GoogleGeminiService, OllamaService,
                                  OpenAIService, GoogleVertexService)
  --max_retries INTEGER           The maximum number of retries to use for the
                                  service. Default is 2. (Applies to:
                                  ClaudeService, GoogleGeminiService,
                                  OllamaService, OpenAIService,
                                  GoogleVertexService)
  --retry_wait_time INTEGER       The wait time between retries. Default is 3.
                                  (Applies to: ClaudeService,
                                  GoogleGeminiService, OllamaService,
                                  OpenAIService, GoogleVertexService)
  --claude_model_name TEXT        The name of the Google model to use for the
                                  service. Default is
                                  claude-3-7-sonnet-20250219. (Applies to:
                                  ClaudeService)
  --claude_api_key TEXT           The Claude API key to use for the service.
                                  Default is None. (Applies to: ClaudeService)
  --max_claude_tokens INTEGER     The maximum number of tokens to use for a
                                  single Claude request. Default is 8192.
                                  (Applies to: ClaudeService)
  --gemini_model_name TEXT        The name of the Google model to use for the
                                  service. Default is gemini-2.0-flash.
                                  (Applies to: GoogleGeminiService,
                                  GoogleVertexService)
  --gemini_api_key TEXT           The Google API key to use for the service.
                                  Default is None. (Applies to:
                                  GoogleGeminiService)
  --ollama_base_url TEXT          The base url to use for ollama.  No trailing
                                  slash. Default is http://localhost:11434.
                                  (Applies to: OllamaService)
  --ollama_model TEXT             The model name to use for ollama. Default is
                                  llama3.2-vision. (Applies to: OllamaService)
  --openai_base_url TEXT          The base url to use for OpenAI-like models.
                                  No trailing slash. Default is
                                  https://api.openai.com/v1. (Applies to:
                                  OpenAIService)
  --openai_model TEXT             The model name to use for OpenAI-like model.
                                  Default is gpt-4o-mini. (Applies to:
                                  OpenAIService)
  --openai_api_key TEXT           The API key to use for the OpenAI-like
                                  service. Default is None. (Applies to:
                                  OpenAIService)
  --vertex_project_id TEXT        Google Cloud Project ID for Vertex AI.
                                  Default is None. (Applies to:
                                  GoogleVertexService)
  --vertex_location TEXT          Google Cloud Location for Vertex AI. Default
                                  is us-central1. (Applies to:
                                  GoogleVertexService)
  --vertex_dedicated              Whether to use a dedicated Vertex AI
                                  instance. Default is False. (Applies to:
                                  GoogleVertexService)
  --page_schema TEXT              The JSON schema to be extracted from the
                                  page. Default is . (Applies to:
                                  PageExtractor)
  --DocumentBuilder_lowres_image_dpi INTEGER
                                  DPI setting for low-resolution page images
                                  used for Layout and Line Detection. Default
                                  is 96.
  --DocumentBuilder_highres_image_dpi INTEGER
                                  DPI setting for high-resolution page images
                                  used for OCR. Default is 192.
  --DocumentBuilder_disable_ocr   Disable OCR processing. Default is False.
  --LayoutBuilder_layout_batch_size OPTIONAL
                                  The batch size to use for the layout model.
                                  Default is None, which will use the default
                                  batch size for the model.
  --LayoutBuilder_force_layout_block TEXT
                                  Skip layout and force every page to be
                                  treated as a specific block type. Default is
                                  None.
  --LayoutBuilder_disable_tqdm    Disable tqdm progress bars. Default is
                                  False.
  --LineBuilder_detection_batch_size OPTIONAL
                                  The batch size to use for the detection
                                  model. Default is None, which will use the
                                  default batch size for the model.
  --LineBuilder_ocr_error_batch_size OPTIONAL
                                  The batch size to use for the ocr error
                                  detection model. Default is None, which will
                                  use the default batch size for the model.
  --LineBuilder_enable_table_ocr  Whether to skip OCR on tables.  The
                                  TableProcessor will re-OCR them.  Only
                                  enable if the TableProcessor is not running.
                                  Default is False.
  --LineBuilder_format_lines      Enable good provider lines to be checked and
                                  fixed by the OCR model Default is False.
  --LineBuilder_layout_coverage_min_lines INTEGER
                                  The minimum number of PdfProvider lines that
                                  must be covered by the layout model to
                                  consider the lines from the PdfProvider
                                  valid. Default is 1.
  --LineBuilder_layout_coverage_threshold FLOAT
                                  The minimum coverage ratio required for the
                                  layout model to consider the lines from the
                                  PdfProvider valid. Default is 0.25.
  --LineBuilder_min_document_ocr_threshold FLOAT
                                  If less pages than this threshold are good,
                                  OCR will happen in the document.  Otherwise
                                  it will not. Default is 0.85.
  --LineBuilder_provider_line_detected_line_min_overlap_pct FLOAT
                                  The percentage of a provider line that has
                                  to be covered by a detected line Default is
                                  0.1.
  --LineBuilder_line_vertical_merge_threshold INTEGER
                                  The maximum pixel distance between y1s for
                                  two lines to be merged Default is 8.
  --LineBuilder_disable_tqdm      Disable tqdm progress bars. Default is
                                  False.
  --LineBuilder_keep_chars        Keep individual characters. Default is
                                  False.
  --OcrBuilder_recognition_batch_size OPTIONAL
                                  The batch size to use for the recognition
                                  model. Default is None, which will use the
                                  default batch size for the model.
  --OcrBuilder_disable_tqdm       Disable tqdm progress bars. Default is
                                  False.
  --OcrBuilder_ocr_task_name TEXT
                                  The OCR mode to use, see surya for details.
                                  Set to 'ocr_without_boxes' for potentially
                                  better performance, at the expense of
                                  formatting. Default is ocr_with_boxes.
  --OcrBuilder_keep_chars         Keep individual characters. Default is
                                  False.
  --OcrBuilder_disable_ocr_math   Disable inline math recognition in OCR
                                  Default is False.
  --LLMLayoutBuilder_layout_batch_size OPTIONAL
                                  The batch size to use for the layout model.
                                  Default is None, which will use the default
                                  batch size for the model.
  --LLMLayoutBuilder_force_layout_block TEXT
                                  Skip layout and force every page to be
                                  treated as a specific block type. Default is
                                  None.
  --LLMLayoutBuilder_disable_tqdm
                                  Whether to disable the tqdm progress bar.
                                  Default is False.
  --LLMLayoutBuilder_google_api_key TEXT
                                  The Google API key to use for the Gemini
                                  model. Default is .
  --LLMLayoutBuilder_confidence_threshold FLOAT
                                  The confidence threshold to use for
                                  relabeling (anything below is relabeled).
                                  Default is 0.7.
  --LLMLayoutBuilder_picture_height_threshold FLOAT
                                  The height threshold for pictures that may
                                  actually be complex regions. (anything above
                                  this ratio against the page is relabeled)
                                  Default is 0.8.
  --LLMLayoutBuilder_model_name TEXT
                                  The name of the Gemini model to use. Default
                                  is gemini-2.0-flash.
  --LLMLayoutBuilder_max_concurrency INTEGER
                                  The maximum number of concurrent requests to
                                  make to the Gemini model. Default is 3.
  --LLMLayoutBuilder_topk_relabelling_prompt TEXT
                                  The prompt to use for relabelling blocks.
                                  Default is a string containing the Gemini
                                  relabelling prompt.
  --LLMLayoutBuilder_complex_relabeling_prompt TEXT
                                  The prompt to use for complex relabelling
                                  blocks. Default is a string containing the
                                  complex relabelling prompt.
  --StructureBuilder_gap_threshold FLOAT
                                  The minimum gap between blocks to consider
                                  them part of the same group. Default is
                                  0.05.
  --StructureBuilder_list_gap_threshold FLOAT
                                  The minimum gap between list items to
                                  consider them part of the same group.
                                  Default is 0.1.
  --BlockquoteProcessor_min_x_indent FLOAT
                                  The minimum horizontal indentation required
                                  to consider a block as part of a blockquote.
                                  Expressed as a percentage of the block
                                  width. Default is 0.1.
  --BlockquoteProcessor_x_start_tolerance FLOAT
                                  The maximum allowable difference between the
                                  starting x-coordinates of consecutive blocks
                                  to consider them aligned. Expressed as a
                                  percentage of the block width. Default is
                                  0.01.
  --BlockquoteProcessor_x_end_tolerance FLOAT
                                  The maximum allowable difference between the
                                  ending x-coordinates of consecutive blocks
                                  to consider them aligned. Expressed as a
                                  percentage of the block width. Default is
                                  0.01.
  --DebugProcessor_debug_data_folder TEXT
                                  The folder to dump debug data to. Default is
                                  debug_data.
  --DebugProcessor_debug_layout_images
                                  Whether to dump layout debug images. Default
                                  is False.
  --DebugProcessor_debug_pdf_images
                                  Whether to dump PDF debug images. Default is
                                  False.
  --DebugProcessor_debug_json     Whether to dump block debug data. Default is
                                  False.
  --EquationProcessor_model_max_length INTEGER
                                  The maximum number of tokens to allow for
                                  the Recognition model. Default is 1024.
  --EquationProcessor_equation_batch_size OPTIONAL
                                  The batch size to use for the recognition
                                  model while processing equations. Default is
                                  None, which will use the default batch size
                                  for the model.
  --EquationProcessor_disable_tqdm
                                  Whether to disable the tqdm progress bar.
                                  Default is False.
  --IgnoreTextProcessor_common_element_threshold FLOAT
                                  The minimum ratio of pages a text block must
                                  appear on to be considered a common element.
                                  Blocks that meet or exceed this threshold
                                  are marked as common elements. Default is
                                  0.2.
  --IgnoreTextProcessor_common_element_min_blocks INTEGER
                                  The minimum number of occurrences of a text
                                  block within a document to consider it a
                                  common element. This ensures that rare
                                  blocks are not mistakenly flagged. Default
                                  is 3.
  --IgnoreTextProcessor_max_streak INTEGER
                                  The maximum number of consecutive
                                  occurrences of a text block allowed before
                                  it is classified as a common element. Helps
                                  to identify patterns like repeated headers
                                  or footers. Default is 3.
  --IgnoreTextProcessor_text_match_threshold INTEGER
                                  The minimum fuzzy match score (0-100)
                                  required to classify a text block as similar
                                  to a common element. Higher values enforce
                                  stricter matching. Default is 90.
  --LineMergeProcessor_min_merge_pct FLOAT
                                  The minimum percentage of intersection area
                                  to consider merging. Default is 0.015.
  --LineMergeProcessor_block_expand_threshold FLOAT
                                  The percentage of the block width to expand
                                  the bounding box. Default is 0.05.
  --LineMergeProcessor_min_merge_ydist FLOAT
                                  The minimum y distance between lines to
                                  consider merging. Default is 5.
  --LineMergeProcessor_intersection_pct_threshold FLOAT
                                  The total amount of intersection area
                                  concentrated in the max intersection block.
                                  Default is 0.5.
  --LineMergeProcessor_vertical_overlap_pct_threshold FLOAT
                                  The minimum percentage of vertical overlap
                                  to consider merging. Default is 0.8.
  --LineMergeProcessor_use_llm    Whether to use LLMs to improve accuracy.
                                  Default is False.
  --LineNumbersProcessor_strip_numbers_threshold FLOAT
                                  The fraction of lines or tokens in a block
                                  that must be numeric to consider them as
                                  line numbers. Default is 0.6.
  --LineNumbersProcessor_min_lines_in_block INTEGER
                                  The minimum number of lines required in a
                                  block for it to be considered during
                                  processing. Ensures that small blocks are
                                  ignored as they are unlikely to contain
                                  meaningful line numbers. Default is 4.
  --LineNumbersProcessor_min_line_length INTEGER
                                  The minimum length of a line (in characters)
                                  to consider it significant when checking for
                                  numeric prefixes or suffixes. Prevents false
                                  positives for short lines. Default is 10.
  --LineNumbersProcessor_min_line_number_span_ratio FLOAT
                                  The minimum ratio of detected line number
                                  spans to total lines required to treat them
                                  as line numbers. Default is 0.6.
  --ListProcessor_min_x_indent FLOAT
                                  The minimum horizontal indentation required
                                  to consider a block as a nested list item.
                                  This is expressed as a percentage of the
                                  page width and is used to determine
                                  hierarchical relationships within a list.
                                  Default is 0.01.
  --LLMComplexRegionProcessor_max_concurrency INTEGER
                                  The maximum number of concurrent requests to
                                  make to the Gemini model. Default is 3.
  --LLMComplexRegionProcessor_image_expansion_ratio FLOAT
                                  The ratio to expand the image by when
                                  cropping. Default is 0.01.
  --LLMComplexRegionProcessor_use_llm
                                  Whether to use the LLM model. Default is
                                  False.
  --LLMComplexRegionProcessor_disable_tqdm
                                  Whether to disable the tqdm progress bar.
                                  Default is False.
  --LLMEquationProcessor_max_concurrency INTEGER
                                  The maximum number of concurrent requests to
                                  make to the Gemini model. Default is 3.
  --LLMEquationProcessor_image_expansion_ratio FLOAT
                                  The ratio to expand the image by when
                                  cropping. Default is 0.05.
  --LLMEquationProcessor_use_llm  Whether to use the LLM model. Default is
                                  False.
  --LLMEquationProcessor_disable_tqdm
                                  Whether to disable the tqdm progress bar.
                                  Default is False.
  --LLMEquationProcessor_min_equation_height FLOAT
                                  The minimum ratio between equation height
                                  and page height to consider for processing.
                                  Default is 0.06.
  --LLMEquationProcessor_redo_inline_math
                                  Whether to redo inline math blocks. Default
                                  is False.
  --LLMEquationProcessor_equation_latex_prompt TEXT
                                  The prompt to use for generating LaTeX from
                                  equations. Default is a string containing
                                  the Gemini prompt.
  --LLMFormProcessor_max_concurrency INTEGER
                                  The maximum number of concurrent requests to
                                  make to the Gemini model. Default is 3.
  --LLMFormProcessor_image_expansion_ratio FLOAT
                                  The ratio to expand the image by when
                                  cropping. Default is 0.01.
  --LLMFormProcessor_use_llm      Whether to use the LLM model. Default is
                                  False.
  --LLMFormProcessor_disable_tqdm
                                  Whether to disable the tqdm progress bar.
                                  Default is False.
  --LLMHandwritingProcessor_max_concurrency INTEGER
                                  The maximum number of concurrent requests to
                                  make to the Gemini model. Default is 3.
  --LLMHandwritingProcessor_image_expansion_ratio FLOAT
                                  The ratio to expand the image by when
                                  cropping. Default is 0.01.
  --LLMHandwritingProcessor_use_llm
                                  Whether to use the LLM model. Default is
                                  False.
  --LLMHandwritingProcessor_disable_tqdm
                                  Whether to disable the tqdm progress bar.
                                  Default is False.
  --LLMHandwritingProcessor_handwriting_generation_prompt TEXT
                                  The prompt to use for OCRing handwriting.
                                  Default is a string containing the Gemini
                                  prompt.
  --LLMImageDescriptionProcessor_max_concurrency INTEGER
                                  The maximum number of concurrent requests to
                                  make to the Gemini model. Default is 3.
  --LLMImageDescriptionProcessor_image_expansion_ratio FLOAT
                                  The ratio to expand the image by when
                                  cropping. Default is 0.01.
  --LLMImageDescriptionProcessor_use_llm
                                  Whether to use the LLM model. Default is
                                  False.
  --LLMImageDescriptionProcessor_disable_tqdm
                                  Whether to disable the tqdm progress bar.
                                  Default is False.
  --LLMImageDescriptionProcessor_extract_images BOOLEAN
                                  Extract images from the document. Default is
                                  True.
  --LLMImageDescriptionProcessor_image_description_prompt TEXT
                                  The prompt to use for generating image
                                  descriptions. Default is a string containing
                                  the Gemini prompt.
  --LLMMathBlockProcessor_max_concurrency INTEGER
                                  The maximum number of concurrent requests to
                                  make to the Gemini model. Default is 3.
  --LLMMathBlockProcessor_image_expansion_ratio FLOAT
                                  The ratio to expand the image by when
                                  cropping. Default is 0.01.
  --LLMMathBlockProcessor_use_llm
                                  Whether to use the LLM model. Default is
                                  False.
  --LLMMathBlockProcessor_disable_tqdm
                                  Whether to disable the tqdm progress bar.
                                  Default is False.
  --LLMMathBlockProcessor_redo_inline_math
                                  If True, the inline math will be re-done,
                                  otherwise it will be left as is. Default is
                                  False.
  --LLMMathBlockProcessor_inlinemath_min_ratio FLOAT
                                  If more than this ratio of blocks are
                                  inlinemath blocks, assume everything has
                                  math. Default is 0.4.
  --LLMSimpleBlockMetaProcessor_max_concurrency INTEGER
                                  The maximum number of concurrent requests to
                                  make to the Gemini model. Default is 3.
  --LLMSimpleBlockMetaProcessor_image_expansion_ratio FLOAT
                                  The ratio to expand the image by when
                                  cropping. Default is 0.01.
  --LLMSimpleBlockMetaProcessor_use_llm
                                  Whether to use the LLM model. Default is
                                  False.
  --LLMSimpleBlockMetaProcessor_disable_tqdm
                                  Whether to disable the tqdm progress bar.
                                  Default is False.
  --LLMTableProcessor_max_concurrency INTEGER
                                  The maximum number of concurrent requests to
                                  make to the Gemini model. Default is 3.
  --LLMTableProcessor_image_expansion_ratio FLOAT
                                  The ratio to expand the image by when
                                  cropping. Default is 0.01.
  --LLMTableProcessor_use_llm     Whether to use the LLM model. Default is
                                  False.
  --LLMTableProcessor_disable_tqdm
                                  Whether to disable the tqdm progress bar.
                                  Default is False.
  --LLMTableProcessor_max_rows_per_batch INTEGER
                                  If the table has more rows than this, chunk
                                  the table. (LLMs can be inaccurate with a
                                  lot of rows) Default is 60.
  --LLMTableProcessor_max_table_rows INTEGER
                                  The maximum number of rows in a table to
                                  process with the LLM processor.  Beyond this
                                  will be skipped. Default is 175.
  --LLMTableProcessor_table_image_expansion_ratio FLOAT
                                  The ratio to expand the image by when
                                  cropping. Default is 0.
  --LLMTableProcessor_rotation_max_wh_ratio FLOAT
                                  The maximum width/height ratio for table
                                  cells for a table to be considered rotated.
                                  Default is 0.6.
  --LLMTableProcessor_table_rewriting_prompt TEXT
                                  The prompt to use for rewriting text.
                                  Default is a string containing the Gemini
                                  rewriting prompt.
  --LLMTableMergeProcessor_max_concurrency INTEGER
                                  The maximum number of concurrent requests to
                                  make to the Gemini model. Default is 3.
  --LLMTableMergeProcessor_image_expansion_ratio FLOAT
                                  The ratio to expand the image by when
                                  cropping. Default is 0.01.
  --LLMTableMergeProcessor_use_llm
                                  Whether to use the LLM model. Default is
                                  False.
  --LLMTableMergeProcessor_disable_tqdm
                                  Whether to disable the tqdm progress bar.
                                  Default is False.
  --LLMTableMergeProcessor_table_height_threshold FLOAT
                                  The minimum height ratio relative to the
                                  page for the first table in a pair to be
                                  considered for merging. Default is 0.6.
  --LLMTableMergeProcessor_table_start_threshold FLOAT
                                  The maximum percentage down the page the
                                  second table can start to be considered for
                                  merging. Default is 0.2.
  --LLMTableMergeProcessor_vertical_table_height_threshold FLOAT
                                  The height tolerance for 2 adjacent tables
                                  to be merged into one. Default is 0.25.
  --LLMTableMergeProcessor_vertical_table_distance_threshold INTEGER
                                  The maximum distance between table edges for
                                  adjacency. Default is 20.
  --LLMTableMergeProcessor_horizontal_table_width_threshold FLOAT
                                  The width tolerance for 2 adjacent tables to
                                  be merged into one. Default is 0.25.
  --LLMTableMergeProcessor_horizontal_table_distance_threshold INTEGER
                                  The maximum distance between table edges for
                                  adjacency. Default is 10.
  --LLMTableMergeProcessor_column_gap_threshold INTEGER
                                  The maximum gap between columns to merge
                                  tables Default is 50.
  --LLMTableMergeProcessor_table_merge_prompt TEXT
                                  The prompt to use for rewriting text.
                                  Default is a string containing the Gemini
                                  rewriting prompt.
  --SectionHeaderProcessor_level_count INTEGER
                                  The number of levels to use for headings.
                                  Default is 4.
  --SectionHeaderProcessor_merge_threshold FLOAT
                                  The minimum gap between headings to consider
                                  them part of the same group. Default is
                                  0.25.
  --SectionHeaderProcessor_default_level INTEGER
                                  The default heading level to use if no
                                  heading level is detected. Default is 2.
  --SectionHeaderProcessor_height_tolerance FLOAT
                                  The minimum height of a heading to consider
                                  it a heading. Default is 0.99.
  --TableProcessor_detect_boxes   Whether to detect boxes for the table
                                  recognition model. Default is False.
  --TableProcessor_detection_batch_size INTEGER
                                  The batch size to use for the table
                                  detection model. Default is None, which will
                                  use the default batch size for the model.
  --TableProcessor_table_rec_batch_size INTEGER
                                  The batch size to use for the table
                                  recognition model. Default is None, which
                                  will use the default batch size for the
                                  model.
  --TableProcessor_recognition_batch_size INTEGER
                                  The batch size to use for the table
                                  recognition model. Default is None, which
                                  will use the default batch size for the
                                  model.
  --TableProcessor_row_split_threshold FLOAT
                                  The percentage of rows that need to be split
                                  across the table before row splitting is
                                  active. Default is 0.5.
  --TableProcessor_pdftext_workers INTEGER
                                  The number of workers to use for pdftext.
                                  Default is 1.
  --TableProcessor_disable_tqdm   Whether to disable the tqdm progress bar.
                                  Default is False.
  --TableProcessor_format_lines   Whether to format the lines. Default is
                                  False.
  --TextProcessor_column_gap_ratio FLOAT
                                  The minimum ratio of the page width to the
                                  column gap to consider a column break.
                                  Default is 0.02.
  --ExtractionConverter_use_llm   Enable higher quality processing with LLMs.
                                  Default is False.
  --ExtractionConverter_pattern TEXT
                                  Default is {\d+\}-{48}\n\n.
  --PdfConverter_use_llm          Enable higher quality processing with LLMs.
                                  Default is False.
  --OCRConverter_use_llm          Enable higher quality processing with LLMs.
                                  Default is False.
  --TableConverter_use_llm        Enable higher quality processing with LLMs.
                                  Default is False.
  --DocumentProvider_pdftext_workers INTEGER
                                  The number of workers to use for pdftext.
                                  Default is 4.
  --DocumentProvider_flatten_pdf BOOLEAN
                                  Whether to flatten the PDF structure.
                                  Default is True.
  --DocumentProvider_force_ocr    Whether to force OCR on the whole document.
                                  Default is False.
  --DocumentProvider_ocr_space_threshold FLOAT
                                  The minimum ratio of spaces to non-spaces to
                                  detect bad text. Default is 0.7.
  --DocumentProvider_ocr_newline_threshold FLOAT
                                  The minimum ratio of newlines to non-
                                  newlines to detect bad text. Default is 0.6.
  --DocumentProvider_ocr_alphanum_threshold FLOAT
                                  The minimum ratio of alphanumeric characters
                                  to non-alphanumeric characters to consider
                                  an alphanumeric character. Default is 0.3.
  --DocumentProvider_image_threshold FLOAT
                                  The minimum coverage ratio of the image to
                                  the page to consider skipping the page.
                                  Default is 0.65.
  --DocumentProvider_strip_existing_ocr
                                  Whether to strip existing OCR text from the
                                  PDF. Default is False.
  --DocumentProvider_disable_links
                                  Whether to disable links. Default is False.
  --PdfProvider_pdftext_workers INTEGER
                                  The number of workers to use for pdftext.
                                  Default is 4.
  --PdfProvider_flatten_pdf BOOLEAN
                                  Whether to flatten the PDF structure.
                                  Default is True.
  --PdfProvider_force_ocr         Whether to force OCR on the whole document.
                                  Default is False.
  --PdfProvider_ocr_space_threshold FLOAT
                                  The minimum ratio of spaces to non-spaces to
                                  detect bad text. Default is 0.7.
  --PdfProvider_ocr_newline_threshold FLOAT
                                  The minimum ratio of newlines to non-
                                  newlines to detect bad text. Default is 0.6.
  --PdfProvider_ocr_alphanum_threshold FLOAT
                                  The minimum ratio of alphanumeric characters
                                  to non-alphanumeric characters to consider
                                  an alphanumeric character. Default is 0.3.
  --PdfProvider_image_threshold FLOAT
                                  The minimum coverage ratio of the image to
                                  the page to consider skipping the page.
                                  Default is 0.65.
  --PdfProvider_strip_existing_ocr
                                  Whether to strip existing OCR text from the
                                  PDF. Default is False.
  --PdfProvider_disable_links     Whether to disable links. Default is False.
  --EpubProvider_pdftext_workers INTEGER
                                  The number of workers to use for pdftext.
                                  Default is 4.
  --EpubProvider_flatten_pdf BOOLEAN
                                  Whether to flatten the PDF structure.
                                  Default is True.
  --EpubProvider_force_ocr        Whether to force OCR on the whole document.
                                  Default is False.
  --EpubProvider_ocr_space_threshold FLOAT
                                  The minimum ratio of spaces to non-spaces to
                                  detect bad text. Default is 0.7.
  --EpubProvider_ocr_newline_threshold FLOAT
                                  The minimum ratio of newlines to non-
                                  newlines to detect bad text. Default is 0.6.
  --EpubProvider_ocr_alphanum_threshold FLOAT
                                  The minimum ratio of alphanumeric characters
                                  to non-alphanumeric characters to consider
                                  an alphanumeric character. Default is 0.3.
  --EpubProvider_image_threshold FLOAT
                                  The minimum coverage ratio of the image to
                                  the page to consider skipping the page.
                                  Default is 0.65.
  --EpubProvider_strip_existing_ocr
                                  Whether to strip existing OCR text from the
                                  PDF. Default is False.
  --EpubProvider_disable_links    Whether to disable links. Default is False.
  --HTMLProvider_pdftext_workers INTEGER
                                  The number of workers to use for pdftext.
                                  Default is 4.
  --HTMLProvider_flatten_pdf BOOLEAN
                                  Whether to flatten the PDF structure.
                                  Default is True.
  --HTMLProvider_force_ocr        Whether to force OCR on the whole document.
                                  Default is False.
  --HTMLProvider_ocr_space_threshold FLOAT
                                  The minimum ratio of spaces to non-spaces to
                                  detect bad text. Default is 0.7.
  --HTMLProvider_ocr_newline_threshold FLOAT
                                  The minimum ratio of newlines to non-
                                  newlines to detect bad text. Default is 0.6.
  --HTMLProvider_ocr_alphanum_threshold FLOAT
                                  The minimum ratio of alphanumeric characters
                                  to non-alphanumeric characters to consider
                                  an alphanumeric character. Default is 0.3.
  --HTMLProvider_image_threshold FLOAT
                                  The minimum coverage ratio of the image to
                                  the page to consider skipping the page.
                                  Default is 0.65.
  --HTMLProvider_strip_existing_ocr
                                  Whether to strip existing OCR text from the
                                  PDF. Default is False.
  --HTMLProvider_disable_links    Whether to disable links. Default is False.
  --ImageProvider_image_count INTEGER
                                  Default is 1.
  --PowerPointProvider_pdftext_workers INTEGER
                                  The number of workers to use for pdftext.
                                  Default is 4.
  --PowerPointProvider_flatten_pdf BOOLEAN
                                  Whether to flatten the PDF structure.
                                  Default is True.
  --PowerPointProvider_force_ocr  Whether to force OCR on the whole document.
                                  Default is False.
  --PowerPointProvider_ocr_space_threshold FLOAT
                                  The minimum ratio of spaces to non-spaces to
                                  detect bad text. Default is 0.7.
  --PowerPointProvider_ocr_newline_threshold FLOAT
                                  The minimum ratio of newlines to non-
                                  newlines to detect bad text. Default is 0.6.
  --PowerPointProvider_ocr_alphanum_threshold FLOAT
                                  The minimum ratio of alphanumeric characters
                                  to non-alphanumeric characters to consider
                                  an alphanumeric character. Default is 0.3.
  --PowerPointProvider_image_threshold FLOAT
                                  The minimum coverage ratio of the image to
                                  the page to consider skipping the page.
                                  Default is 0.65.
  --PowerPointProvider_strip_existing_ocr
                                  Whether to strip existing OCR text from the
                                  PDF. Default is False.
  --PowerPointProvider_disable_links
                                  Whether to disable links. Default is False.
  --PowerPointProvider_include_slide_number
                                  Default is False.
  --SpreadSheetProvider_pdftext_workers INTEGER
                                  The number of workers to use for pdftext.
                                  Default is 4.
  --SpreadSheetProvider_flatten_pdf BOOLEAN
                                  Whether to flatten the PDF structure.
                                  Default is True.
  --SpreadSheetProvider_force_ocr
                                  Whether to force OCR on the whole document.
                                  Default is False.
  --SpreadSheetProvider_ocr_space_threshold FLOAT
                                  The minimum ratio of spaces to non-spaces to
                                  detect bad text. Default is 0.7.
  --SpreadSheetProvider_ocr_newline_threshold FLOAT
                                  The minimum ratio of newlines to non-
                                  newlines to detect bad text. Default is 0.6.
  --SpreadSheetProvider_ocr_alphanum_threshold FLOAT
                                  The minimum ratio of alphanumeric characters
                                  to non-alphanumeric characters to consider
                                  an alphanumeric character. Default is 0.3.
  --SpreadSheetProvider_image_threshold FLOAT
                                  The minimum coverage ratio of the image to
                                  the page to consider skipping the page.
                                  Default is 0.65.
  --SpreadSheetProvider_strip_existing_ocr
                                  Whether to strip existing OCR text from the
                                  PDF. Default is False.
  --SpreadSheetProvider_disable_links
                                  Whether to disable links. Default is False.
  --ExtractionRenderer_extract_images BOOLEAN
                                  Extract images from the document. Default is
                                  True.
  --HTMLRenderer_extract_images BOOLEAN
                                  Extract images from the document. Default is
                                  True.
  --HTMLRenderer_paginate_output  Whether to paginate the output. Default is
                                  False.
  --JSONRenderer_extract_images BOOLEAN
                                  Extract images from the document. Default is
                                  True.
  --MarkdownRenderer_extract_images BOOLEAN
                                  Extract images from the document. Default is
                                  True.
  --MarkdownRenderer_paginate_output
                                  Whether to paginate the output. Default is
                                  False.
  --MarkdownRenderer_page_separator TEXT
                                  The separator to use between pages. Default
                                  is '-' * 48.
  --OCRJSONRenderer_extract_images BOOLEAN
                                  Extract images from the document. Default is
                                  True.
  --ClaudeService_timeout INTEGER
                                  The timeout to use for the service. Default
                                  is 30.
  --ClaudeService_max_retries INTEGER
                                  The maximum number of retries to use for the
                                  service. Default is 2.
  --ClaudeService_retry_wait_time INTEGER
                                  The wait time between retries. Default is 3.
  --ClaudeService_claude_model_name TEXT
                                  The name of the Google model to use for the
                                  service. Default is
                                  claude-3-7-sonnet-20250219.
  --ClaudeService_claude_api_key TEXT
                                  The Claude API key to use for the service.
                                  Default is None.
  --ClaudeService_max_claude_tokens INTEGER
                                  The maximum number of tokens to use for a
                                  single Claude request. Default is 8192.
  --GoogleGeminiService_timeout INTEGER
                                  The timeout to use for the service. Default
                                  is 30.
  --GoogleGeminiService_max_retries INTEGER
                                  The maximum number of retries to use for the
                                  service. Default is 2.
  --GoogleGeminiService_retry_wait_time INTEGER
                                  The wait time between retries. Default is 3.
  --GoogleGeminiService_gemini_model_name TEXT
                                  The name of the Google model to use for the
                                  service. Default is gemini-2.0-flash.
  --GoogleGeminiService_gemini_api_key TEXT
                                  The Google API key to use for the service.
                                  Default is None.
  --OllamaService_timeout INTEGER
                                  The timeout to use for the service. Default
                                  is 30.
  --OllamaService_max_retries INTEGER
                                  The maximum number of retries to use for the
                                  service. Default is 2.
  --OllamaService_retry_wait_time INTEGER
                                  The wait time between retries. Default is 3.
  --OllamaService_ollama_base_url TEXT
                                  The base url to use for ollama.  No trailing
                                  slash. Default is http://localhost:11434.
  --OllamaService_ollama_model TEXT
                                  The model name to use for ollama. Default is
                                  llama3.2-vision.
  --OpenAIService_timeout INTEGER
                                  The timeout to use for the service. Default
                                  is 30.
  --OpenAIService_max_retries INTEGER
                                  The maximum number of retries to use for the
                                  service. Default is 2.
  --OpenAIService_retry_wait_time INTEGER
                                  The wait time between retries. Default is 3.
  --OpenAIService_openai_base_url TEXT
                                  The base url to use for OpenAI-like models.
                                  No trailing slash. Default is
                                  https://api.openai.com/v1.
  --OpenAIService_openai_model TEXT
                                  The model name to use for OpenAI-like model.
                                  Default is gpt-4o-mini.
  --OpenAIService_openai_api_key TEXT
                                  The API key to use for the OpenAI-like
                                  service. Default is None.
  --GoogleVertexService_timeout INTEGER
                                  The timeout to use for the service. Default
                                  is 30.
  --GoogleVertexService_max_retries INTEGER
                                  The maximum number of retries to use for the
                                  service. Default is 2.
  --GoogleVertexService_retry_wait_time INTEGER
                                  The wait time between retries. Default is 3.
  --GoogleVertexService_gemini_model_name TEXT
                                  The name of the Google model to use for the
                                  service. Default is gemini-2.0-flash-001.
  --GoogleVertexService_vertex_project_id TEXT
                                  Google Cloud Project ID for Vertex AI.
                                  Default is None.
  --GoogleVertexService_vertex_location TEXT
                                  Google Cloud Location for Vertex AI. Default
                                  is us-central1.
  --GoogleVertexService_vertex_dedicated
                                  Whether to use a dedicated Vertex AI
                                  instance. Default is False.
  --PageExtractor_max_concurrency INTEGER
                                  The maximum number of concurrent requests to
                                  make to the Gemini model. Default is 3.
  --PageExtractor_disable_tqdm    Whether to disable the tqdm progress bar.
                                  Default is False.
  --PageExtractor_page_schema TEXT
                                  The JSON schema to be extracted from the
                                  page. Default is .
  --help                          Show this message and exit.
```


### `marker config --help`


```
Here is a list of all the Builders, Processors, Converters, Providers and Renderers in Marker along with their attributes:
Builders:

  DocumentBuilder: 
Constructs a Document given a PdfProvider, LayoutBuilder, and OcrBuilder.

    Attributes:
        lowres_image_dpi (int):
            DPI setting for low-resolution page images used for Layout and Line Detection.
            Default is 96.
        highres_image_dpi (int):
            DPI setting for high-resolution page images used for OCR.
            Default is 192.
        disable_ocr (bool):
            Disable OCR processing.
            Default is False.

  LayoutBuilder: 
A builder for performing layout detection on PDF pages and merging the results into the document.

    Attributes:
        layout_batch_size (Optional[int]):
            The batch size to use for the layout model.
            Default is None, which will use the default batch size for the model.
        force_layout_block (str):
            Skip layout and force every page to be treated as a specific block type.
            Default is None.
        disable_tqdm (bool):
            Disable tqdm progress bars.
            Default is False.

  LineBuilder: 
A builder for detecting text lines. Merges the detected lines with the lines from the provider

    Attributes:
        detection_batch_size (Optional[int]):
            The batch size to use for the detection model.
            Default is None, which will use the default batch size for the model.
        ocr_error_batch_size (Optional[int]):
            The batch size to use for the ocr error detection model.
            Default is None, which will use the default batch size for the model.
        enable_table_ocr (bool):
            Whether to skip OCR on tables.  The TableProcessor will re-OCR them.  Only enable if the TableProcessor is not running.
            Default is False.
        format_lines (bool):
            Enable good provider lines to be checked and fixed by the OCR model
            Default is False.
        layout_coverage_min_lines (int):
            The minimum number of PdfProvider lines that must be covered by the layout model
            to consider the lines from the PdfProvider valid.
            Default is 1.
        layout_coverage_threshold (float):
            The minimum coverage ratio required for the layout model to consider
            the lines from the PdfProvider valid.
            Default is 0.25.
        min_document_ocr_threshold (float):
            If less pages than this threshold are good, OCR will happen in the document.  Otherwise it will not.
            Default is 0.85.
        provider_line_detected_line_min_overlap_pct (float):
            The percentage of a provider line that has to be covered by a detected line
            Default is 0.1.
        line_vertical_merge_threshold (int):
            The maximum pixel distance between y1s for two lines to be merged
            Default is 8.
        excluded_for_coverage (Tuple[marker.schema.BlockTypes]):
            A list of block types to exclude from the layout coverage check.
            Default is (<BlockTypes.Figure: '11'>, <BlockTypes.Picture: '20'>, <BlockTypes.Table: '22'>, <BlockTypes.FigureGroup: '4'>, <BlockTypes.TableGroup: '5'>, <BlockTypes.PictureGroup: '7'>).
        ocr_remove_blocks (Tuple[marker.schema.BlockTypes, ...]):
            Default is (<BlockTypes.Table: '22'>, <BlockTypes.Form: '13'>, <BlockTypes.TableOfContents: '24'>, <BlockTypes.Equation: '14'>).
        disable_tqdm (bool):
            Disable tqdm progress bars.
            Default is False.
        keep_chars (bool):
            Keep individual characters.
            Default is False.

  OcrBuilder: 
A builder for performing OCR on PDF pages and merging the results into the document.

    Attributes:
        recognition_batch_size (Optional[int]):
            The batch size to use for the recognition model.
            Default is None, which will use the default batch size for the model.
        disable_tqdm (bool):
            Disable tqdm progress bars.
            Default is False.
        skip_ocr_blocks (List[marker.schema.BlockTypes]):
            Blocktypes for which contained lines are not processed by the OCR modelBy default, this avoids recognizing lines inside equations
            Default is Equation.
        ocr_task_name (str):
            The OCR mode to use, see surya for details.  Set to 'ocr_without_boxes' for potentially better performance, at the expense of formatting.
            Default is ocr_with_boxes.
        keep_chars (bool):
            Keep individual characters.
            Default is False.
        disable_ocr_math (bool):
            Disable inline math recognition in OCR
            Default is False.

  LLMLayoutBuilder: 
A builder for relabelling blocks to improve the quality of the layout.

    Attributes:
        layout_batch_size (Optional[int]):
            The batch size to use for the layout model.
            Default is None, which will use the default batch size for the model.
        force_layout_block (str):
            Skip layout and force every page to be treated as a specific block type.
            Default is None.
        disable_tqdm (bool):
            Whether to disable the tqdm progress bar.
            Default is False.
        google_api_key (str):
            The Google API key to use for the Gemini model.
            Default is .
        confidence_threshold (float):
            The confidence threshold to use for relabeling (anything below is relabeled).
            Default is 0.7.
        picture_height_threshold (float):
            The height threshold for pictures that may actually be complex regions. (anything above this ratio against the page is relabeled)
            Default is 0.8.
        model_name (str):
            The name of the Gemini model to use.
            Default is gemini-2.0-flash.
        max_concurrency (int):
            The maximum number of concurrent requests to make to the Gemini model.
            Default is 3.
        topk_relabelling_prompt (str):
            The prompt to use for relabelling blocks.
            Default is a string containing the Gemini relabelling prompt.
        complex_relabeling_prompt (str):
            The prompt to use for complex relabelling blocks.
            Default is a string containing the complex relabelling prompt.

  StructureBuilder: 
A builder for grouping blocks together based on their structure.

    Attributes:
        gap_threshold (float):
            The minimum gap between blocks to consider them part of the same group.
            Default is 0.05.
        list_gap_threshold (float):
            The minimum gap between list items to consider them part of the same group.
            Default is 0.1.
Processors:

  BlockquoteProcessor: 
A processor for tagging blockquotes.

    Attributes:
        block_types (Tuple[marker.schema.BlockTypes]):
            The block types to process.
            Default is (<BlockTypes.Text: '23'>, <BlockTypes.TextInlineMath: '16'>).
        min_x_indent (float):
            The minimum horizontal indentation required to consider a block as part of a blockquote.
            Expressed as a percentage of the block width.
            Default is 0.1.
        x_start_tolerance (float):
            The maximum allowable difference between the starting x-coordinates of consecutive blocks to consider them aligned.
            Expressed as a percentage of the block width.
            Default is 0.01.
        x_end_tolerance (float):
            The maximum allowable difference between the ending x-coordinates of consecutive blocks to consider them aligned.
            Expressed as a percentage of the block width.
            Default is 0.01.

  CodeProcessor: 
A processor for formatting code blocks.

    Attributes:
        block_types (Optional[typing.Tuple[marker.schema.BlockTypes]]):
            Default is (<BlockTypes.Code: '10'>,).

  DebugProcessor: 
A processor for debugging the document.

    Attributes:
        block_types (tuple):
            The block types to process.
            Default is an empty tuple.
        debug_data_folder (str):
            The folder to dump debug data to.
            Default is debug_data.
        debug_layout_images (bool):
            Whether to dump layout debug images.
            Default is False.
        debug_pdf_images (bool):
            Whether to dump PDF debug images.
            Default is False.
        debug_json (bool):
            Whether to dump block debug data.
            Default is False.

  DocumentTOCProcessor: 
A processor for generating a table of contents for the document.

    Attributes:
        block_types (Optional[typing.Tuple[marker.schema.BlockTypes]]):
            Default is (<BlockTypes.SectionHeader: '21'>,).

  EquationProcessor: 
A processor for recognizing equations in the document.

    Attributes:
        block_types (Tuple[marker.schema.BlockTypes]):
            The block types to process.
            Default is (<BlockTypes.Equation: '14'>,).
        model_max_length (int):
            The maximum number of tokens to allow for the Recognition model.
            Default is 1024.
        equation_batch_size (Optional[int]):
            The batch size to use for the recognition model while processing equations.
            Default is None, which will use the default batch size for the model.
        disable_tqdm (bool):
            Whether to disable the tqdm progress bar.
            Default is False.

  FootnoteProcessor: 
A processor for pushing footnotes to the bottom, and relabeling mislabeled text blocks.

    Attributes:
        block_types (Optional[typing.Tuple[marker.schema.BlockTypes]]):
            Default is (<BlockTypes.Footnote: '12'>,).

  IgnoreTextProcessor: 
A processor for identifying and ignoring common text blocks in a document. 
These blocks often represent repetitive or non-essential elements, such as headers, footers, or page numbers.

    Attributes:
        block_types (Optional[typing.Tuple[marker.schema.BlockTypes]]):
            Default is (<BlockTypes.Text: '23'>, <BlockTypes.SectionHeader: '21'>, <BlockTypes.TextInlineMath: '16'>).
        common_element_threshold (float):
            The minimum ratio of pages a text block must appear on to be considered a common element.
            Blocks that meet or exceed this threshold are marked as common elements.
            Default is 0.2.
        common_element_min_blocks (int):
            The minimum number of occurrences of a text block within a document to consider it a common element.
            This ensures that rare blocks are not mistakenly flagged.
            Default is 3.
        max_streak (int):
            The maximum number of consecutive occurrences of a text block allowed before it is classified as a common element.
            Helps to identify patterns like repeated headers or footers.
            Default is 3.
        text_match_threshold (int):
            The minimum fuzzy match score (0-100) required to classify a text block as similar to a common element.
            Higher values enforce stricter matching.
            Default is 90.

  LineMergeProcessor: 
A processor for merging inline math lines.

    Attributes:
        block_types (Optional[typing.Tuple[marker.schema.BlockTypes]]):
            Default is (<BlockTypes.Text: '23'>, <BlockTypes.TextInlineMath: '16'>, <BlockTypes.Caption: '9'>, <BlockTypes.Footnote: '12'>, <BlockTypes.SectionHeader: '21'>).
        min_merge_pct (float):
            The minimum percentage of intersection area to consider merging.
            Default is 0.015.
        block_expand_threshold (float):
            The percentage of the block width to expand the bounding box.
            Default is 0.05.
        min_merge_ydist (float):
            The minimum y distance between lines to consider merging.
            Default is 5.
        intersection_pct_threshold (float):
            The total amount of intersection area concentrated in the max intersection block.
            Default is 0.5.
        vertical_overlap_pct_threshold (float):
            The minimum percentage of vertical overlap to consider merging.
            Default is 0.8.
        use_llm (bool):
            Whether to use LLMs to improve accuracy.
            Default is False.

  LineNumbersProcessor: 
A processor for ignoring line numbers.

    Attributes:
        block_types (Optional[typing.Tuple[marker.schema.BlockTypes]]):
            Default is (<BlockTypes.Text: '23'>, <BlockTypes.TextInlineMath: '16'>).
        strip_numbers_threshold (float):
            The fraction of lines or tokens in a block that must be numeric to consider them as line numbers.
            Default is 0.6.
        min_lines_in_block (int):
            The minimum number of lines required in a block for it to be considered during processing.
            Ensures that small blocks are ignored as they are unlikely to contain meaningful line numbers.
            Default is 4.
        min_line_length (int):
            The minimum length of a line (in characters) to consider it significant when checking for
            numeric prefixes or suffixes. Prevents false positives for short lines.
            Default is 10.
        min_line_number_span_ratio (float):
            The minimum ratio of detected line number spans to total lines required to treat them as line numbers.
            Default is 0.6.

  ListProcessor: 
A processor for merging lists across pages and columns

    Attributes:
        block_types (Optional[typing.Tuple[marker.schema.BlockTypes]]):
            Default is (<BlockTypes.ListGroup: '6'>,).
        ignored_block_types (Tuple[marker.schema.BlockTypes]):
            The list of block types to ignore when merging lists.
            Default is (<BlockTypes.PageHeader: '19'>, <BlockTypes.PageFooter: '18'>).
        min_x_indent (float):
            The minimum horizontal indentation required to consider a block as a nested list item.
            This is expressed as a percentage of the page width and is used to determine hierarchical relationships within a list.
            Default is 0.01.

  LLMComplexRegionProcessor: 
    Attributes:
        block_types (Optional[typing.Tuple[marker.schema.BlockTypes]]):
            Default is (<BlockTypes.ComplexRegion: '26'>,).
        max_concurrency (int):
            The maximum number of concurrent requests to make to the Gemini model.
            Default is 3.
        image_expansion_ratio (float):
            The ratio to expand the image by when cropping.
            Default is 0.01.
        use_llm (bool):
            Whether to use the LLM model.
            Default is False.
        disable_tqdm (bool):
            Whether to disable the tqdm progress bar.
            Default is False.

  LLMEquationProcessor: 
    Attributes:
        block_types (Optional[typing.Tuple[marker.schema.BlockTypes]]):
            Default is (<BlockTypes.Equation: '14'>,).
        max_concurrency (int):
            The maximum number of concurrent requests to make to the Gemini model.
            Default is 3.
        image_expansion_ratio (float):
            The ratio to expand the image by when cropping.
            Default is 0.05.
        use_llm (bool):
            Whether to use the LLM model.
            Default is False.
        disable_tqdm (bool):
            Whether to disable the tqdm progress bar.
            Default is False.
        min_equation_height (float):
            The minimum ratio between equation height and page height to consider for processing.
            Default is 0.06.
        redo_inline_math (bool):
            Whether to redo inline math blocks.
            Default is False.
        equation_latex_prompt (str):
            The prompt to use for generating LaTeX from equations.
            Default is a string containing the Gemini prompt.

  LLMFormProcessor: 
    Attributes:
        block_types (Optional[typing.Tuple[marker.schema.BlockTypes]]):
            Default is (<BlockTypes.Form: '13'>,).
        max_concurrency (int):
            The maximum number of concurrent requests to make to the Gemini model.
            Default is 3.
        image_expansion_ratio (float):
            The ratio to expand the image by when cropping.
            Default is 0.01.
        use_llm (bool):
            Whether to use the LLM model.
            Default is False.
        disable_tqdm (bool):
            Whether to disable the tqdm progress bar.
            Default is False.

  LLMHandwritingProcessor: 
    Attributes:
        block_types (Optional[typing.Tuple[marker.schema.BlockTypes]]):
            Default is (<BlockTypes.Handwriting: '15'>, <BlockTypes.Text: '23'>).
        max_concurrency (int):
            The maximum number of concurrent requests to make to the Gemini model.
            Default is 3.
        image_expansion_ratio (float):
            The ratio to expand the image by when cropping.
            Default is 0.01.
        use_llm (bool):
            Whether to use the LLM model.
            Default is False.
        disable_tqdm (bool):
            Whether to disable the tqdm progress bar.
            Default is False.
        handwriting_generation_prompt (str):
            The prompt to use for OCRing handwriting.
            Default is a string containing the Gemini prompt.

  LLMImageDescriptionProcessor: 
    Attributes:
        block_types (Optional[typing.Tuple[marker.schema.BlockTypes]]):
            Default is (<BlockTypes.Picture: '20'>, <BlockTypes.Figure: '11'>).
        max_concurrency (int):
            The maximum number of concurrent requests to make to the Gemini model.
            Default is 3.
        image_expansion_ratio (float):
            The ratio to expand the image by when cropping.
            Default is 0.01.
        use_llm (bool):
            Whether to use the LLM model.
            Default is False.
        disable_tqdm (bool):
            Whether to disable the tqdm progress bar.
            Default is False.
        extract_images (bool):
            Extract images from the document.
            Default is True.
        image_description_prompt (str):
            The prompt to use for generating image descriptions.
            Default is a string containing the Gemini prompt.

  LLMMathBlockProcessor: 
    Attributes:
        block_types (Optional[typing.Tuple[marker.schema.BlockTypes]]):
            Default is (<BlockTypes.TextInlineMath: '16'>,).
        max_concurrency (int):
            The maximum number of concurrent requests to make to the Gemini model.
            Default is 3.
        image_expansion_ratio (float):
            The ratio to expand the image by when cropping.
            Default is 0.01.
        use_llm (bool):
            Whether to use the LLM model.
            Default is False.
        disable_tqdm (bool):
            Whether to disable the tqdm progress bar.
            Default is False.
        redo_inline_math (bool):
            If True, the inline math will be re-done, otherwise it will be left as is.
            Default is False.
        inlinemath_min_ratio (float):
            If more than this ratio of blocks are inlinemath blocks, assume everything has math.
            Default is 0.4.

  LLMSimpleBlockMetaProcessor: 
A wrapper for simple LLM processors, so they can all run in parallel.

    Attributes:
        block_types (Optional[typing.Tuple[marker.schema.BlockTypes]]):
            Default is None.
        max_concurrency (int):
            The maximum number of concurrent requests to make to the Gemini model.
            Default is 3.
        image_expansion_ratio (float):
            The ratio to expand the image by when cropping.
            Default is 0.01.
        use_llm (bool):
            Whether to use the LLM model.
            Default is False.
        disable_tqdm (bool):
            Whether to disable the tqdm progress bar.
            Default is False.

  LLMTableProcessor: 
    Attributes:
        block_types (Tuple[marker.schema.BlockTypes]):
            The block types to process.
            Default is (<BlockTypes.Table: '22'>, <BlockTypes.TableOfContents: '24'>).
        max_concurrency (int):
            The maximum number of concurrent requests to make to the Gemini model.
            Default is 3.
        image_expansion_ratio (float):
            The ratio to expand the image by when cropping.
            Default is 0.01.
        use_llm (bool):
            Whether to use the LLM model.
            Default is False.
        disable_tqdm (bool):
            Whether to disable the tqdm progress bar.
            Default is False.
        max_rows_per_batch (int):
            If the table has more rows than this, chunk the table. (LLMs can be inaccurate with a lot of rows)
            Default is 60.
        max_table_rows (int):
            The maximum number of rows in a table to process with the LLM processor.  Beyond this will be skipped.
            Default is 175.
        table_image_expansion_ratio (float):
            The ratio to expand the image by when cropping.
            Default is 0.
        rotation_max_wh_ratio (float):
            The maximum width/height ratio for table cells for a table to be considered rotated.
            Default is 0.6.
        table_rewriting_prompt (str):
            The prompt to use for rewriting text.
            Default is a string containing the Gemini rewriting prompt.

  LLMTableMergeProcessor: 
    Attributes:
        block_types (Tuple[marker.schema.BlockTypes]):
            The block types to process.
            Default is (<BlockTypes.Table: '22'>, <BlockTypes.TableOfContents: '24'>).
        max_concurrency (int):
            The maximum number of concurrent requests to make to the Gemini model.
            Default is 3.
        image_expansion_ratio (float):
            The ratio to expand the image by when cropping.
            Default is 0.01.
        use_llm (bool):
            Whether to use the LLM model.
            Default is False.
        disable_tqdm (bool):
            Whether to disable the tqdm progress bar.
            Default is False.
        table_height_threshold (float):
            The minimum height ratio relative to the page for the first table in a pair to be considered for merging.
            Default is 0.6.
        table_start_threshold (float):
            The maximum percentage down the page the second table can start to be considered for merging.
            Default is 0.2.
        vertical_table_height_threshold (float):
            The height tolerance for 2 adjacent tables to be merged into one.
            Default is 0.25.
        vertical_table_distance_threshold (int):
            The maximum distance between table edges for adjacency.
            Default is 20.
        horizontal_table_width_threshold (float):
            The width tolerance for 2 adjacent tables to be merged into one.
            Default is 0.25.
        horizontal_table_distance_threshold (int):
            The maximum distance between table edges for adjacency.
            Default is 10.
        column_gap_threshold (int):
            The maximum gap between columns to merge tables
            Default is 50.
        table_merge_prompt (str):
            The prompt to use for rewriting text.
            Default is a string containing the Gemini rewriting prompt.

  OrderProcessor: 
A processor for sorting the blocks in order if needed.  This can help when the layout image was sliced.

    Attributes:
        block_types (Optional[typing.Tuple[marker.schema.BlockTypes]]):
            Default is ().

  PageHeaderProcessor: 
A processor for moving PageHeaders to the top

    Attributes:
        block_types (Optional[typing.Tuple[marker.schema.BlockTypes]]):
            Default is (<BlockTypes.PageHeader: '19'>,).

  ReferenceProcessor: 
A processor for adding references to the document.

    Attributes:
        block_types (Optional[typing.Tuple[marker.schema.BlockTypes]]):
            Default is None.

  SectionHeaderProcessor: 
A processor for recognizing section headers in the document.

    Attributes:
        block_types (Optional[typing.Tuple[marker.schema.BlockTypes]]):
            Default is (<BlockTypes.SectionHeader: '21'>,).
        level_count (int):
            The number of levels to use for headings.
            Default is 4.
        merge_threshold (float):
            The minimum gap between headings to consider them part of the same group.
            Default is 0.25.
        default_level (int):
            The default heading level to use if no heading level is detected.
            Default is 2.
        height_tolerance (float):
            The minimum height of a heading to consider it a heading.
            Default is 0.99.

  TableProcessor: 
A processor for recognizing tables in the document.

    Attributes:
        block_types (Optional[typing.Tuple[marker.schema.BlockTypes]]):
            Default is (<BlockTypes.Table: '22'>, <BlockTypes.TableOfContents: '24'>, <BlockTypes.Form: '13'>).
        detect_boxes (bool):
            Whether to detect boxes for the table recognition model.
            Default is False.
        detection_batch_size (int):
            The batch size to use for the table detection model.
            Default is None, which will use the default batch size for the model.
        table_rec_batch_size (int):
            The batch size to use for the table recognition model.
            Default is None, which will use the default batch size for the model.
        recognition_batch_size (int):
            The batch size to use for the table recognition model.
            Default is None, which will use the default batch size for the model.
        contained_block_types (List[marker.schema.BlockTypes]):
            Block types to remove if they're contained inside the tables.
            Default is (<BlockTypes.Text: '23'>, <BlockTypes.TextInlineMath: '16'>).
        row_split_threshold (float):
            The percentage of rows that need to be split across the table before row splitting is active.
            Default is 0.5.
        pdftext_workers (int):
            The number of workers to use for pdftext.
            Default is 1.
        disable_tqdm (bool):
            Whether to disable the tqdm progress bar.
            Default is False.
        format_lines (bool):
            Whether to format the lines.
            Default is False.

  TextProcessor: 
A processor for merging text across pages and columns.

    Attributes:
        block_types (Optional[typing.Tuple[marker.schema.BlockTypes]]):
            Default is (<BlockTypes.Text: '23'>, <BlockTypes.TextInlineMath: '16'>).
        column_gap_ratio (float):
            The minimum ratio of the page width to the column gap to consider a column break.
            Default is 0.02.
Converters:

  ExtractionConverter: 
    Attributes:
        override_map (Dict[marker.schema.BlockTypes, typing.Type[marker.schema.blocks.base.Block]]):
            A mapping to override the default block classes for specific block types.
            The keys are `BlockTypes` enum values, representing the types of blocks,
            and the values are corresponding `Block` class implementations to use
            instead of the defaults.
            Default is defaultdict(None, {}).
        use_llm (bool):
            Enable higher quality processing with LLMs.
            Default is False.
        default_processors (Tuple[marker.processors.BaseProcessor, ...]):
            Default is (<class 'marker.processors.order.OrderProcessor'>, <class 'marker.processors.line_merge.LineMergeProcessor'>, <class 'marker.processors.blockquote.BlockquoteProcessor'>, <class 'marker.processors.code.CodeProcessor'>, <class 'marker.processors.document_toc.DocumentTOCProcessor'>, <class 'marker.processors.equation.EquationProcessor'>, <class 'marker.processors.footnote.FootnoteProcessor'>, <class 'marker.processors.ignoretext.IgnoreTextProcessor'>, <class 'marker.processors.line_numbers.LineNumbersProcessor'>, <class 'marker.processors.list.ListProcessor'>, <class 'marker.processors.page_header.PageHeaderProcessor'>, <class 'marker.processors.sectionheader.SectionHeaderProcessor'>, <class 'marker.processors.table.TableProcessor'>, <class 'marker.processors.llm.llm_table.LLMTableProcessor'>, <class 'marker.processors.llm.llm_table_merge.LLMTableMergeProcessor'>, <class 'marker.processors.llm.llm_form.LLMFormProcessor'>, <class 'marker.processors.text.TextProcessor'>, <class 'marker.processors.llm.llm_complex.LLMComplexRegionProcessor'>, <class 'marker.processors.llm.llm_image_description.LLMImageDescriptionProcessor'>, <class 'marker.processors.llm.llm_equation.LLMEquationProcessor'>, <class 'marker.processors.llm.llm_handwriting.LLMHandwritingProcessor'>, <class 'marker.processors.llm.llm_mathblock.LLMMathBlockProcessor'>, <class 'marker.processors.reference.ReferenceProcessor'>, <class 'marker.processors.debug.DebugProcessor'>).
        default_llm_service (BaseService):
            Default is <class 'marker.services.gemini.GoogleGeminiService'>.
        pattern (str):
            Default is {\d+\}-{48}\n\n.

  PdfConverter: 
A converter for processing and rendering PDF files into Markdown, JSON, HTML and other formats.

    Attributes:
        override_map (Dict[marker.schema.BlockTypes, typing.Type[marker.schema.blocks.base.Block]]):
            A mapping to override the default block classes for specific block types.
            The keys are `BlockTypes` enum values, representing the types of blocks,
            and the values are corresponding `Block` class implementations to use
            instead of the defaults.
            Default is defaultdict(None, {}).
        use_llm (bool):
            Enable higher quality processing with LLMs.
            Default is False.
        default_processors (Tuple[marker.processors.BaseProcessor, ...]):
            Default is (<class 'marker.processors.order.OrderProcessor'>, <class 'marker.processors.line_merge.LineMergeProcessor'>, <class 'marker.processors.blockquote.BlockquoteProcessor'>, <class 'marker.processors.code.CodeProcessor'>, <class 'marker.processors.document_toc.DocumentTOCProcessor'>, <class 'marker.processors.equation.EquationProcessor'>, <class 'marker.processors.footnote.FootnoteProcessor'>, <class 'marker.processors.ignoretext.IgnoreTextProcessor'>, <class 'marker.processors.line_numbers.LineNumbersProcessor'>, <class 'marker.processors.list.ListProcessor'>, <class 'marker.processors.page_header.PageHeaderProcessor'>, <class 'marker.processors.sectionheader.SectionHeaderProcessor'>, <class 'marker.processors.table.TableProcessor'>, <class 'marker.processors.llm.llm_table.LLMTableProcessor'>, <class 'marker.processors.llm.llm_table_merge.LLMTableMergeProcessor'>, <class 'marker.processors.llm.llm_form.LLMFormProcessor'>, <class 'marker.processors.text.TextProcessor'>, <class 'marker.processors.llm.llm_complex.LLMComplexRegionProcessor'>, <class 'marker.processors.llm.llm_image_description.LLMImageDescriptionProcessor'>, <class 'marker.processors.llm.llm_equation.LLMEquationProcessor'>, <class 'marker.processors.llm.llm_handwriting.LLMHandwritingProcessor'>, <class 'marker.processors.llm.llm_mathblock.LLMMathBlockProcessor'>, <class 'marker.processors.reference.ReferenceProcessor'>, <class 'marker.processors.debug.DebugProcessor'>).
        default_llm_service (BaseService):
            Default is <class 'marker.services.gemini.GoogleGeminiService'>.

  OCRConverter: 
    Attributes:
        override_map (Dict[marker.schema.BlockTypes, typing.Type[marker.schema.blocks.base.Block]]):
            A mapping to override the default block classes for specific block types.
            The keys are `BlockTypes` enum values, representing the types of blocks,
            and the values are corresponding `Block` class implementations to use
            instead of the defaults.
            Default is defaultdict(None, {}).
        use_llm (bool):
            Enable higher quality processing with LLMs.
            Default is False.
        default_processors (Tuple[marker.processors.BaseProcessor, ...]):
            Default is (<class 'marker.processors.equation.EquationProcessor'>,).
        default_llm_service (BaseService):
            Default is <class 'marker.services.gemini.GoogleGeminiService'>.

  TableConverter: 
    Attributes:
        override_map (Dict[marker.schema.BlockTypes, typing.Type[marker.schema.blocks.base.Block]]):
            A mapping to override the default block classes for specific block types.
            The keys are `BlockTypes` enum values, representing the types of blocks,
            and the values are corresponding `Block` class implementations to use
            instead of the defaults.
            Default is defaultdict(None, {}).
        use_llm (bool):
            Enable higher quality processing with LLMs.
            Default is False.
        default_processors (Tuple[marker.processors.BaseProcessor, ...]):
            Default is (<class 'marker.processors.table.TableProcessor'>, <class 'marker.processors.llm.llm_table.LLMTableProcessor'>, <class 'marker.processors.llm.llm_table_merge.LLMTableMergeProcessor'>, <class 'marker.processors.llm.llm_form.LLMFormProcessor'>, <class 'marker.processors.llm.llm_complex.LLMComplexRegionProcessor'>).
        default_llm_service (BaseService):
            Default is <class 'marker.services.gemini.GoogleGeminiService'>.
        converter_block_types (List[marker.schema.BlockTypes]):
            Default is (<BlockTypes.Table: '22'>, <BlockTypes.Form: '13'>, <BlockTypes.TableOfContents: '24'>).
Providers:

  DocumentProvider: 
    Attributes:
        page_range (Optional[typing.List[int]]):
            The range of pages to process.
            Default is None, which will process all pages.
        pdftext_workers (int):
            The number of workers to use for pdftext.
            Default is 4.
        flatten_pdf (bool):
            Whether to flatten the PDF structure.
            Default is True.
        force_ocr (bool):
            Whether to force OCR on the whole document.
            Default is False.
        ocr_invalid_chars (tuple):
            The characters to consider invalid for OCR.
            Default is ('�', '�').
        ocr_space_threshold (float):
            The minimum ratio of spaces to non-spaces to detect bad text.
            Default is 0.7.
        ocr_newline_threshold (float):
            The minimum ratio of newlines to non-newlines to detect bad text.
            Default is 0.6.
        ocr_alphanum_threshold (float):
            The minimum ratio of alphanumeric characters to non-alphanumeric characters to consider an alphanumeric character.
            Default is 0.3.
        image_threshold (float):
            The minimum coverage ratio of the image to the page to consider skipping the page.
            Default is 0.65.
        strip_existing_ocr (bool):
            Whether to strip existing OCR text from the PDF.
            Default is False.
        disable_links (bool):
            Whether to disable links.
            Default is False.

  PdfProvider: 
A provider for PDF files.

    Attributes:
        page_range (Optional[typing.List[int]]):
            The range of pages to process.
            Default is None, which will process all pages.
        pdftext_workers (int):
            The number of workers to use for pdftext.
            Default is 4.
        flatten_pdf (bool):
            Whether to flatten the PDF structure.
            Default is True.
        force_ocr (bool):
            Whether to force OCR on the whole document.
            Default is False.
        ocr_invalid_chars (tuple):
            The characters to consider invalid for OCR.
            Default is ('�', '�').
        ocr_space_threshold (float):
            The minimum ratio of spaces to non-spaces to detect bad text.
            Default is 0.7.
        ocr_newline_threshold (float):
            The minimum ratio of newlines to non-newlines to detect bad text.
            Default is 0.6.
        ocr_alphanum_threshold (float):
            The minimum ratio of alphanumeric characters to non-alphanumeric characters to consider an alphanumeric character.
            Default is 0.3.
        image_threshold (float):
            The minimum coverage ratio of the image to the page to consider skipping the page.
            Default is 0.65.
        strip_existing_ocr (bool):
            Whether to strip existing OCR text from the PDF.
            Default is False.
        disable_links (bool):
            Whether to disable links.
            Default is False.

  EpubProvider: 
    Attributes:
        page_range (Optional[typing.List[int]]):
            The range of pages to process.
            Default is None, which will process all pages.
        pdftext_workers (int):
            The number of workers to use for pdftext.
            Default is 4.
        flatten_pdf (bool):
            Whether to flatten the PDF structure.
            Default is True.
        force_ocr (bool):
            Whether to force OCR on the whole document.
            Default is False.
        ocr_invalid_chars (tuple):
            The characters to consider invalid for OCR.
            Default is ('�', '�').
        ocr_space_threshold (float):
            The minimum ratio of spaces to non-spaces to detect bad text.
            Default is 0.7.
        ocr_newline_threshold (float):
            The minimum ratio of newlines to non-newlines to detect bad text.
            Default is 0.6.
        ocr_alphanum_threshold (float):
            The minimum ratio of alphanumeric characters to non-alphanumeric characters to consider an alphanumeric character.
            Default is 0.3.
        image_threshold (float):
            The minimum coverage ratio of the image to the page to consider skipping the page.
            Default is 0.65.
        strip_existing_ocr (bool):
            Whether to strip existing OCR text from the PDF.
            Default is False.
        disable_links (bool):
            Whether to disable links.
            Default is False.

  HTMLProvider: 
    Attributes:
        page_range (Optional[typing.List[int]]):
            The range of pages to process.
            Default is None, which will process all pages.
        pdftext_workers (int):
            The number of workers to use for pdftext.
            Default is 4.
        flatten_pdf (bool):
            Whether to flatten the PDF structure.
            Default is True.
        force_ocr (bool):
            Whether to force OCR on the whole document.
            Default is False.
        ocr_invalid_chars (tuple):
            The characters to consider invalid for OCR.
            Default is ('�', '�').
        ocr_space_threshold (float):
            The minimum ratio of spaces to non-spaces to detect bad text.
            Default is 0.7.
        ocr_newline_threshold (float):
            The minimum ratio of newlines to non-newlines to detect bad text.
            Default is 0.6.
        ocr_alphanum_threshold (float):
            The minimum ratio of alphanumeric characters to non-alphanumeric characters to consider an alphanumeric character.
            Default is 0.3.
        image_threshold (float):
            The minimum coverage ratio of the image to the page to consider skipping the page.
            Default is 0.65.
        strip_existing_ocr (bool):
            Whether to strip existing OCR text from the PDF.
            Default is False.
        disable_links (bool):
            Whether to disable links.
            Default is False.

  ImageProvider: 
    Attributes:
        page_range (Optional[typing.List[int]]):
            The range of pages to process.
            Default is None, which will process all pages.
        image_count (int):
            Default is 1.

  PowerPointProvider: 
    Attributes:
        page_range (Optional[typing.List[int]]):
            The range of pages to process.
            Default is None, which will process all pages.
        pdftext_workers (int):
            The number of workers to use for pdftext.
            Default is 4.
        flatten_pdf (bool):
            Whether to flatten the PDF structure.
            Default is True.
        force_ocr (bool):
            Whether to force OCR on the whole document.
            Default is False.
        ocr_invalid_chars (tuple):
            The characters to consider invalid for OCR.
            Default is ('�', '�').
        ocr_space_threshold (float):
            The minimum ratio of spaces to non-spaces to detect bad text.
            Default is 0.7.
        ocr_newline_threshold (float):
            The minimum ratio of newlines to non-newlines to detect bad text.
            Default is 0.6.
        ocr_alphanum_threshold (float):
            The minimum ratio of alphanumeric characters to non-alphanumeric characters to consider an alphanumeric character.
            Default is 0.3.
        image_threshold (float):
            The minimum coverage ratio of the image to the page to consider skipping the page.
            Default is 0.65.
        strip_existing_ocr (bool):
            Whether to strip existing OCR text from the PDF.
            Default is False.
        disable_links (bool):
            Whether to disable links.
            Default is False.
        include_slide_number (bool):
            Default is False.

  SpreadSheetProvider: 
    Attributes:
        page_range (Optional[typing.List[int]]):
            The range of pages to process.
            Default is None, which will process all pages.
        pdftext_workers (int):
            The number of workers to use for pdftext.
            Default is 4.
        flatten_pdf (bool):
            Whether to flatten the PDF structure.
            Default is True.
        force_ocr (bool):
            Whether to force OCR on the whole document.
            Default is False.
        ocr_invalid_chars (tuple):
            The characters to consider invalid for OCR.
            Default is ('�', '�').
        ocr_space_threshold (float):
            The minimum ratio of spaces to non-spaces to detect bad text.
            Default is 0.7.
        ocr_newline_threshold (float):
            The minimum ratio of newlines to non-newlines to detect bad text.
            Default is 0.6.
        ocr_alphanum_threshold (float):
            The minimum ratio of alphanumeric characters to non-alphanumeric characters to consider an alphanumeric character.
            Default is 0.3.
        image_threshold (float):
            The minimum coverage ratio of the image to the page to consider skipping the page.
            Default is 0.65.
        strip_existing_ocr (bool):
            Whether to strip existing OCR text from the PDF.
            Default is False.
        disable_links (bool):
            Whether to disable links.
            Default is False.
Renderers:

  ExtractionRenderer: 
    Attributes:
        image_blocks (Tuple[marker.schema.BlockTypes, ...]):
            The block types to consider as images.
            Default is (<BlockTypes.Picture: '20'>, <BlockTypes.Figure: '11'>).
        extract_images (bool):
            Extract images from the document.
            Default is True.
        image_extraction_mode (Literal['lowres', 'highres']):
            The mode to use for extracting images.
            Default is highres.

  HTMLRenderer: 
A renderer for HTML output.

    Attributes:
        image_blocks (Tuple[marker.schema.BlockTypes, ...]):
            The block types to consider as images.
            Default is (<BlockTypes.Picture: '20'>, <BlockTypes.Figure: '11'>).
        extract_images (bool):
            Extract images from the document.
            Default is True.
        image_extraction_mode (Literal['lowres', 'highres']):
            The mode to use for extracting images.
            Default is highres.
        page_blocks (Tuple[marker.schema.BlockTypes]):
            The block types to consider as pages.
            Default is (<BlockTypes.Page: '8'>,).
        paginate_output (bool):
            Whether to paginate the output.
            Default is False.

  JSONRenderer: 
A renderer for JSON output.

    Attributes:
        image_blocks (Tuple[marker.schema.BlockTypes]):
            The list of block types to consider as images.
            Default is (<BlockTypes.Picture: '20'>, <BlockTypes.Figure: '11'>).
        extract_images (bool):
            Extract images from the document.
            Default is True.
        image_extraction_mode (Literal['lowres', 'highres']):
            The mode to use for extracting images.
            Default is highres.
        page_blocks (Tuple[marker.schema.BlockTypes]):
            The list of block types to consider as pages.
            Default is (<BlockTypes.Page: '8'>,).

  MarkdownRenderer: 
    Attributes:
        image_blocks (Tuple[marker.schema.BlockTypes, ...]):
            The block types to consider as images.
            Default is (<BlockTypes.Picture: '20'>, <BlockTypes.Figure: '11'>).
        extract_images (bool):
            Extract images from the document.
            Default is True.
        image_extraction_mode (Literal['lowres', 'highres']):
            The mode to use for extracting images.
            Default is highres.
        page_blocks (Tuple[marker.schema.BlockTypes]):
            The block types to consider as pages.
            Default is (<BlockTypes.Page: '8'>,).
        paginate_output (bool):
            Whether to paginate the output.
            Default is False.
        page_separator (str):
            The separator to use between pages.
            Default is '-' * 48.
        inline_math_delimiters (Tuple[str]):
            The delimiters to use for inline math.
            Default is ('$', '$').
        block_math_delimiters (Tuple[str]):
            The delimiters to use for block math.
            Default is ('$$', '$$').

  OCRJSONRenderer: 
A renderer for OCR JSON output.

    Attributes:
        image_blocks (Tuple[marker.schema.BlockTypes]):
            The list of block types to consider as images.
            Default is (<BlockTypes.Picture: '20'>, <BlockTypes.Figure: '11'>).
        extract_images (bool):
            Extract images from the document.
            Default is True.
        image_extraction_mode (Literal['lowres', 'highres']):
            The mode to use for extracting images.
            Default is highres.
        page_blocks (Tuple[marker.schema.BlockTypes]):
            The list of block types to consider as pages.
            Default is (<BlockTypes.Page: '8'>,).
Services:

  ClaudeService: 
    Attributes:
        timeout (int):
            The timeout to use for the service.
            Default is 30.
        max_retries (int):
            The maximum number of retries to use for the service.
            Default is 2.
        retry_wait_time (int):
            The wait time between retries.
            Default is 3.
        claude_model_name (str):
            The name of the Google model to use for the service.
            Default is claude-3-7-sonnet-20250219.
        claude_api_key (str):
            The Claude API key to use for the service.
            Default is None.
        max_claude_tokens (int):
            The maximum number of tokens to use for a single Claude request.
            Default is 8192.

  GoogleGeminiService: 
    Attributes:
        timeout (int):
            The timeout to use for the service.
            Default is 30.
        max_retries (int):
            The maximum number of retries to use for the service.
            Default is 2.
        retry_wait_time (int):
            The wait time between retries.
            Default is 3.
        gemini_model_name (str):
            The name of the Google model to use for the service.
            Default is gemini-2.0-flash.
        gemini_api_key (str):
            The Google API key to use for the service.
            Default is None.

  OllamaService: 
    Attributes:
        timeout (int):
            The timeout to use for the service.
            Default is 30.
        max_retries (int):
            The maximum number of retries to use for the service.
            Default is 2.
        retry_wait_time (int):
            The wait time between retries.
            Default is 3.
        ollama_base_url (str):
            The base url to use for ollama.  No trailing slash.
            Default is http://localhost:11434.
        ollama_model (str):
            The model name to use for ollama.
            Default is llama3.2-vision.

  OpenAIService: 
    Attributes:
        timeout (int):
            The timeout to use for the service.
            Default is 30.
        max_retries (int):
            The maximum number of retries to use for the service.
            Default is 2.
        retry_wait_time (int):
            The wait time between retries.
            Default is 3.
        openai_base_url (str):
            The base url to use for OpenAI-like models.  No trailing slash.
            Default is https://api.openai.com/v1.
        openai_model (str):
            The model name to use for OpenAI-like model.
            Default is gpt-4o-mini.
        openai_api_key (str):
            The API key to use for the OpenAI-like service.
            Default is None.

  GoogleVertexService: 
    Attributes:
        timeout (int):
            The timeout to use for the service.
            Default is 30.
        max_retries (int):
            The maximum number of retries to use for the service.
            Default is 2.
        retry_wait_time (int):
            The wait time between retries.
            Default is 3.
        gemini_model_name (str):
            The name of the Google model to use for the service.
            Default is gemini-2.0-flash-001.
        vertex_project_id (str):
            Google Cloud Project ID for Vertex AI.
            Default is None.
        vertex_location (str):
            Google Cloud Location for Vertex AI.
            Default is us-central1.
        vertex_dedicated (bool):
            Whether to use a dedicated Vertex AI instance.
            Default is False.
Extractors:

  PageExtractor: 
An extractor that pulls data from a single page.

    Attributes:
        max_concurrency (int):
            The maximum number of concurrent requests to make to the Gemini model.
            Default is 3.
        disable_tqdm (bool):
            Whether to disable the tqdm progress bar.
            Default is False.
        page_schema (str):
            The JSON schema to be extracted from the page.
            Default is .
```