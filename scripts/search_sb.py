#!/usr/bin/env python3
import asyncio, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.config.settings import load_config
from src.tools.secondbrain_tools import SecondBrainTools

async def main():
    if len(sys.argv) < 2:
        print("用法：python search_sb.py <查询> [模式] [数量]")
        sys.exit(1)
    query, mode, top_k = sys.argv[1], sys.argv[2] if len(sys.argv)>2 else "hybrid", int(sys.argv[3]) if len(sys.argv)>3 else 5
    tools = SecondBrainTools(load_config())
    results = await tools.search_notes({"query": query, "mode": mode, "max_results": top_k})
    print(f"🔍 {query} ({mode}):")
    for i, r in enumerate(results, 1):
        d = json.loads(r)
        print(f"[{i}] [{d['vault_name']}] {d['file_path'].split('/')[-1]}: {d['content'][:80]}...")

asyncio.run(main())
