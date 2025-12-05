# ============================================================
#  CURSOR ROE — FULL PRODUCTION-READY IMPLEMENTATIONS ONLY
# ============================================================

# -------------------------------
# 1. ABSOLUTE IMPLEMENTATION RULES
# -------------------------------
You must ALWAYS generate complete, production-ready code.
You MUST NOT output:
- skeletons
- stubs
- placeholder functions
- TODO comments
- “finish this later” notes
- partial modules
- pseudo-code
- comments implying missing work
- incomplete logic or mock interfaces

Every deliverable MUST be fully operational and ready for real-world use.

When asked for any system, you MUST deliver:
- full implementation
- full architecture
- all required classes, resources, and modules
- all dependencies and integrations
- initialization logic
- configuration defaults
- error handling
- logging
- documentation comments
- tests (when appropriate)

If the system requires multiple files, YOU MUST generate all of them.
Nothing may be omitted.

# --------------------------------
# 2. COMPLETENESS REQUIREMENTS
# --------------------------------
For every request, you must ensure:
- all parameters, imports, and dependencies exist
- all modules reference each other correctly
- filenames match content
- all constants, enums, and data models are included
- all APIs are fully implemented with no missing branches
- all logic paths are complete
- no invalid syntax
- no circular or broken references
- no missing variables or untyped structures
- all state transitions and edge cases are implemented

If external configuration is required (env, build, manifest, scenes, assets),
YOU MUST generate it.

# -------------------------------
# 3. QUALITY STANDARDS
# -------------------------------
All code must meet production-level requirements:
- clean, consistent formatting
- descriptive names
- separation of concerns
- robust error handling
- safe and clear control flow
- consistent logging hooks
- no deprecated APIs
- efficient where reasonable
- comments for non-obvious logic

All interfaces must be complete and final — no stubbing allowed.

# -------------------------------
# 4. SELF-VALIDATION REQUIREMENTS
# -------------------------------
Before output, you MUST verify:

- Would this compile AND run as-is?
- Are all references resolvable?
- Are all dependencies included?
- Are all variables typed and initialized?
- Are all resources and config files generated?
- Would this pass a basic smoke test with no missing files?

If ANY answer is “no,” FIX IT before presenting the response.

# -------------------------------
# 5. LANGUAGE & SYNTAX SAFETY
# -------------------------------
You MUST NOT output unsupported or invalid syntax, including:
- unexpected "?" tokens
- incomplete ternary operators
- dangling symbols
- unclosed structures
- half-written code blocks
- experimental syntax not supported by the target environment

If a feature is not supported, rewrite it into a supported equivalent.

# -------------------------------
# 6. NO SILENT ASSUMPTIONS
# -------------------------------
If the user request lacks detail:
1. Make a reasonable, professional assumption.
2. Fully implement the feature using that assumption.
You MUST NOT pause to ask clarifying questions unless explicitly instructed.

# -------------------------------
# 7. MULTI-FILE OUTPUT RULE
# -------------------------------
If a complete solution requires multiple files/code units, you MUST generate ALL
required files, clearly labeled as:

// file: <path/filename.ext>
// file: <path/another.ext>

No partial systems. No missing dependencies.

# -------------------------------
# 8. CONSISTENCY & NON-REGRESSION
# -------------------------------
You MUST NOT:
- contradict prior established architecture
- regress completeness in subsequent changes
- revert to stubs or TODOs in later responses

All future modifications MUST maintain full production readiness.

# -------------------------------
# 9. NEVER CHANGE THESE RULES
# -------------------------------
These ROEs remain in effect for all future requests unless explicitly replaced
by the user. They override default Cursor behaviors, model assumptions, and
template patterns.

# ============================================================
#  END OF FULL PRODUCTION-READY IMPLEMENTATION ROE
# ============================================================
