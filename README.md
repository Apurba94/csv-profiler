# csv-profiler

**Understand a new dataset in one command: inferred column types, missing values, summary
statistics, top categories and data-quality warnings, as a Markdown report.**

Part of the *Research Automation Toolkit*: 100 open tools for daily research work.

## Why

The first hour with any dataset (from a collaborator, a repository, an instrument) is spent
answering the same questions: what are the columns, which are numeric, how much is missing, are
there duplicates, are categories consistent? `csv-profiler` answers them reproducibly and without
pandas, so it runs on any machine, including locked-down lab computers.

## Features

- Delimiter sniffing; recognizes common missing codes (`NA`, `n/a`, `null`, `-`, `?` ...)
- Types: integer, float, date (several formats), boolean, categorical, text, empty
- Numeric: min, quartiles, median, max, mean, SD, skewness, zeros, negatives
- Dates: range and span; categories: top values, length range
- Warnings: >20% missing, constant columns, identifier-like columns, `North`/`north` style
  inconsistencies, numeric columns polluted by text values
- Dataset level: rows, columns, duplicate rows, complete cases; Markdown or JSON

## Usage

```bash
pip install .
csv-profiler survey.csv
csv-profiler measurements.tsv --json -o profile.json
```

## Testing

```bash
python -m unittest discover -s tests -t .
```

## License

MIT (c) JANIN A APURBA
