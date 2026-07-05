Everything needed to write Picat code with LLMs.

1. **An MCP server for Picat,** which enables any tools-capable LLM to run Picat
code in appropriate environments. Tested with llama-ui (of llama.cpp). As
only a tool is included, to run Picat code, further tools for writing files,
reading file, etc should come from another MCP server. Used for this python-mcp-server from pypi.
1. **A compact Picat reference in text form** (1208 lines, 54 KB, about 16k-20k tokens,
depending on the LLM), derived by GLM-5.2 from the Picat user guide from
Picat 3.9#9.
This is very helpful to load in the context, for the LLMs to be very
sure on the syntax, semantic, list of packages, predicates, functions and
operators of Picat when they write Picat code.
