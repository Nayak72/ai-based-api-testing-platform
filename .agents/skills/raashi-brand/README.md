# Raashi Cognitive Technologies — Skill Pack

> **Transforming Knowledge into Intelligent Solutions**

An enterprise-grade design system and AI brand skill pack for Raashi Cognitive Technologies Pvt. Ltd. This skill pack ensures all AI-assisted code generation produces consistent, accessible, high-performance, and beautifully branded user interfaces.

## Directory Overview

```
.agents/skills/raashi-brand/
├── SKILL.md                 # Main agent entry point & skill definitions
├── AGENTS.md                # Agent execution & pre-flight rules
├── README.md                # Skill documentation & setup guide
├── references/              # Detailed design system specs
│   ├── brand-guidelines.md
│   ├── colors.md
│   ├── typography.md
│   ├── spacing.md
│   ├── animations.md
│   ├── iconography.md
│   ├── accessibility.md
│   ├── ui-patterns.md
│   ├── components.md
│   ├── prompts.md
│   ├── dos-and-donts.md
│   └── examples.md
├── tailwind/                # Ready-to-use Tailwind configuration
│   ├── tailwind.config.ts
│   └── globals.css
├── shadcn/                  # Custom shadcn theme CSS
│   └── theme.css
├── tokens/                  # Raw JSON design tokens
│   ├── colors.json
│   ├── spacing.json
│   ├── typography.json
│   ├── shadows.json
│   └── radius.json
└── examples/                # Complete page specifications
    ├── landing-page.md
    ├── dashboard.md
    ├── admin-panel.md
    └── mobile-ui.md
```

## Quick Setup

1. Include `raashi-brand` in your workspace `.agents/skills` directory.
2. Copy `tailwind/tailwind.config.ts` into your Next.js/Vite project root.
3. Import `shadcn/theme.css` into your main layout or `globals.css`.
