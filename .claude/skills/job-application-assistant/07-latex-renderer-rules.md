# LaTeX Renderer Rules

This file is the mechanical rendering specification for converting `cv.md` and `cover.md` into compilable LaTeX. It is loaded only by the `latex-renderer` skill. Editorial guidance (structure, tone, content) lives in `05-cv-templates.md` and `06-cover-letter-templates.md`.

---

## CV Rendering

### Output and compile

- **Output file:** `applications/<company>-<role>/main_<company>.tex`
- **Also copy to:** `cv/main_<company>.tex` (for consistency with existing tooling)
- **Compile with:** `pdflatex` (not xelatex)
- **Template seed:** `cv/main_example.tex`

```bash
cd cv && pdflatex main_<company>.tex && cd ..
```

### Boilerplate (copy verbatim, fill placeholders)

```latex
\documentclass[11pt,a4paper,sans]{moderncv}
\moderncvstyle{banking}
\moderncvcolor{blue}

\usepackage[utf8]{inputenc}
\usepackage{hyperref}
\hypersetup{
    colorlinks=true,
    linkcolor=blue,
    filecolor=magenta,
    urlcolor=blue,
    pdftitle={CANDIDATE_NAME - CV},
    pdfpagemode=FullScreen,
}
\usepackage[scale=0.77]{geometry}
\usepackage{import}

\name{FIRST_NAME}{LAST_NAME}
\address{ADDRESS}{}{}
\phone[mobile]{PHONE}
\email{EMAIL}
\extrainfo{\href{LINKEDIN_URL}{LinkedIn}, \href{GITHUB_URL}{GitHub}}

\begin{document}
\makecvtitle
```

### md → LaTeX section mapping

| `cv.md` element | LaTeX output |
|-----------------|-------------|
| `## Profile` heading + paragraph | `\vspace{6pt}\small{...}` — no `\section` header |
| `## Core Competencies` + bullet list | `\section{Core Competencies}` + `\begin{itemize}` with `\textbf{Category:} detail` per item |
| `## Experience` heading | `\section{Professional Experience}\vspace{3pt}\begin{itemize}` |
| `### Title — Company (YYYY–YYYY) \| City` | `\item{\cventry{YYYY--YYYY}{Title}{Company}{City, Country}{}{\vspace{1pt}` |
| `-` bullets under experience entry | inner `\begin{itemize}\item ...\vspace{1pt}\end{itemize}` |
| `## Education` heading | `\section{Education}\vspace{1pt}\begin{itemize}` |
| `### Degree — Institution (YYYY–YYYY) \| City` | `\item{\cventry{YYYY--YYYY}{Degree in Field}{Institution}{City, Country}{}{\vspace{1pt}` |
| `## Languages` + inline list | `\section{Languages}\vspace{1pt}\begin{itemize}\item ...` |
| `## Publications` + bullet list | `\section{Publications}\vspace{1pt}\begin{itemize}` |
| `## Honors and Awards` + bullet list | `\section{Honors and Awards}\vspace{1pt}\begin{itemize}` |
| `## References` | `\section{References}\vspace{1pt}\begin{itemize}\item{Available upon request.}` |

### `\cventry` syntax

```latex
\item{\cventry{DATE_RANGE}{JOB_TITLE}{COMPANY}{CITY, COUNTRY}{}{\vspace{1pt}
\begin{itemize}
    \item Bullet one.\vspace{1pt}
    \item Bullet two.\vspace{1pt}
    \item Bullet three.
\end{itemize}}}

\vspace{3pt}
```

- Date range uses `--` (en-dash): `2021--2024`
- Close with `}}` (one for `\cventry{}` content, one for `\item{}`)
- Add `\vspace{3pt}` between entries

### Special character escaping (CV)

| Character | Escaped form |
|-----------|-------------|
| `&` | `\&` |
| `_` | `\_` |
| `%` | `\%` |
| `#` | `\#` |
| `~` | `\textasciitilde{}` |
| `^` | `\textasciicircum{}` |
| `{` | `\{` |
| `}` | `\}` |
| `"` (opening) | ` `` ` |
| `"` (closing) | `''` |

---

## Cover Letter Rendering

### Output and compile

- **Output file:** `applications/<company>-<role>/cover_<company>_<role>.tex`
- **Also copy to:** `cover_letters/cover_<company>_<role>.tex`
- **Copy `cover.cls`:** from `cover_letters/cover.cls` to `applications/<company>-<role>/cover.cls`
- **Compile with:** `xelatex` (not pdflatex)
- **Font directory must be present:** `cover_letters/OpenFonts/fonts/` — compile from `cover_letters/` directory

```bash
cd cover_letters && xelatex cover_<company>_<role>.tex && cd ..
```

### Boilerplate (copy verbatim, fill placeholders)

```latex
\documentclass[]{cover}
\usepackage{fancyhdr}

\pagestyle{fancy}
\fancyhf{}

\rfoot{Page \thepage \hspace{0pt}}
\thispagestyle{empty}
\renewcommand{\headrulewidth}{0pt}
\begin{document}

\namesection{}{\Huge{CANDIDATE_NAME}}{
  \href{mailto:EMAIL}{EMAIL} | PHONE | \urlstyle{same}\href{LINKEDIN_URL}{LinkedIn}
}

\currentdate{\today}
```

### md → LaTeX section mapping

| `cover.md` element | LaTeX output |
|--------------------|-------------|
| `Dear X,` line | `\lettercontent{Dear X,}` |
| Regular paragraph | `\lettercontent{paragraph text}` |
| `- bullet` list within paragraph | `\lettercontent{intro text\n\begin{itemize}\n    \item ...\n\end{itemize}\nfollowup text}` |
| `Kind regards,` / closing | `\begin{flushright}\closing{Kind regards,\\}\n\signature{CANDIDATE_NAME}\n\end{flushright}` |

### Key commands reference

| Command | Purpose |
|---------|---------|
| `\namesection{}{Name}{contact}` | Header with name and contact info |
| `\currentdate{\today}` | Date field |
| `\lettercontent{text}` | Body paragraph (adds vertical spacing after) |
| `\closing{text}` | Closing line |
| `\signature{name}` | Printed name below signature |

### Bullet lists inside `\lettercontent`

```latex
\lettercontent{Intro sentence:

\begin{itemize}
    \item \textbf{Category:} detail
    \item \textbf{Category:} detail
    \item \textbf{Category:} detail
\end{itemize}

Follow-up sentence.}
```

### Line spacing (if letter is long)

```latex
\usepackage{setspace}
\setstretch{1.0}
```

Add after `\usepackage{fancyhdr}` if content is near overflow.

### Special character escaping (cover letter)

Same as CV escaping table above. Additionally:
- Em-dash `—` → remove; use comma or period instead
- Ellipsis `...` → `\ldots{}`

---

## Compilation checklist

Before reporting compilation complete:

- [ ] `pdflatex` exits with no errors (warnings about overfull hboxes are acceptable)
- [ ] `xelatex` exits with no errors
- [ ] CV PDF is exactly 2 pages
- [ ] Cover letter PDF is exactly 1 page
- [ ] No placeholder text remaining (`[YOUR_NAME]`, `CANDIDATE_NAME`, etc.)
- [ ] URLs in CV are live links (blue, clickable)
- [ ] Fonts render correctly in cover letter (Lato/Raleway visible)
