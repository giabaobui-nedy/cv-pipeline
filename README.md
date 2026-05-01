# CV Pipeline

Personal CV tailoring pipeline. Source-of-truth content lives in `bullet-bank/`,
job ads to tailor against live in `job-ads/`, the LaTeX CV is assembled in
`cv/`, and compiled PDFs land in `outputs/`.

## Layout

```
cv-pipeline/
  cv/
    main.tex
    sections/
      experience.tex
      projects.tex
      skills.tex
  bullet-bank/        # raw bullets per role/project
  job-ads/            # saved job descriptions to tailor against
  outputs/            # compiled PDFs (gitignored)
```

## Workflow (rough)

1. Drop a job ad into `job-ads/<company>.md`.
2. Pick/rewrite bullets from `bullet-bank/` to best match the ad.
3. Update the relevant `cv/sections/*.tex`.
4. Compile `cv/main.tex` -> PDF into `outputs/`.

See `BOUNDARIES.md` for what must NOT go into this repo.
