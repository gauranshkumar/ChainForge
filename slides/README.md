# Prompt Evolution Lab - Presentation

This is a Slidev presentation about the Prompt Evolution Lab and systematic prompt optimization using evolutionary algorithms.

## Authors
- Gauransh Kumar
- Venilla Sooban

## Setup

1. Install dependencies:
```bash
cd slides
npm install
```

## Running the Presentation

### Development Mode (with live reload)
```bash
npm run dev
```
This will open the presentation at `http://localhost:3030`

### Build for Production
```bash
npm run build
```
The static site will be generated in `dist/`

### Export to PDF
```bash
npm run export
```
This will generate a PDF of the presentation

## Features

- 12 slides covering the complete evolutionary algorithm architecture
- Mermaid diagrams for visual representation
- Minimal text, maximum visual impact
- Covers:
  - Problem statement
  - Evolutionary algorithm overview
  - System architecture
  - Selection operators (Tournament & Roulette Wheel)
  - Novel semantic crossover with spaCy
  - Novel taxonomy-based mutation with Neo4j
  - Data preservation feature
  - Fitness metrics (MCC & Balanced Accuracy)
  - Complete workflow
  - Key innovations

## Navigation

- **Arrow keys**: Navigate between slides
- **Space**: Next slide
- **Shift + Space**: Previous slide
- **f**: Fullscreen mode
- **o**: Overview mode (see all slides)
- **d**: Dark mode toggle

## Presentation Time

Designed for approximately 5 minutes of presentation time.

## Technology Stack

- Slidev: Vue-powered presentation framework
- Mermaid: Diagram generation
- Markdown: Content format
