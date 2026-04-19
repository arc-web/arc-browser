# Quick Start: LLM Integration

## The Simplest Way to Get Started

### 1. Start LLM Studio

- Open LLM Studio
- Load a model (any model works)
- Start the API server (usually port 1234)
- Note the model name shown

### 2. Set These 3 Variables

```bash
export LLM_TYPE=llm-studio
export LLM_BASE_URL=http://localhost:1234/v1
export LLM_MODEL=llama-3-8b-instruct  # Use YOUR model name
```

### 3. Start the Server

```bash
npm start
```

You should see: `✅ LLM Service initialized`

### 4. That's It!

Now you can use `browser_generate_script` to generate Playwright code from natural language.

---

## What Changed?

**Before:** You had to write Playwright code yourself or use rule-based parsing

**Now:** You can say "fill the form and submit" and the LLM generates the code for you

---

## Do I Have To?

**No!** If you don't set the environment variables, everything works the same as before. Only the `browser_generate_script` tool needs LLM.

---

## Need More Help?

See `HOW_TO_USE_LLM.md` for detailed instructions.

