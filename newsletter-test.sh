#!/bin/bash
# Newsletter Test Command - 간단하게 CLI 테스트 명령을 실행하는 셸 스크립트

if [ "$#" -eq 0 ]; then
  echo "Usage: ./newsletter-test.sh <data_file> [options]"
  echo ""
  echo "Data file types:"
  echo "  - render_data_langgraph*.json : Rendered newsletter data (needs recollection in content mode)"
  echo "  - collected_articles_processed.json : Filtered articles with metadata (optimal for content mode)"
  echo "  - collected_articles_raw.json : All collected articles with metadata (usable for content mode)"
  echo ""
  echo "Options:"
  echo "  --output <file>        Specify custom output file path"
  echo "  --mode <mode>          Mode: template (default) or content"
  echo "  --track-cost            Enable LangSmith cost tracking"
  echo ""
  echo "Modes:"
  echo "  template: Just re-render the existing data with the current HTML template"
  echo "  content:  Run the full processing pipeline using saved article data (skips collection)"
  echo ""
  echo "Examples:"
  echo "  ./newsletter-test.sh output/intermediate_processing/collected_articles_processed.json --mode content"
  echo "  ./newsletter-test.sh output/intermediate_processing/collected_articles_raw.json --mode content"
  echo "  ./newsletter-test.sh output/intermediate_processing/render_data_langgraph_20250522_143255.json --mode template"
  echo ""
  echo "Note:"
  echo "  Both raw and processed article files now include all metadata (keywords, domain, etc.)"
  echo "  needed for content mode testing."
  echo ""
  exit 1
fi

echo "Running newsletter test with data file: $1"
python -m newsletter.cli test "$@"
