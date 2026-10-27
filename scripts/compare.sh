#!/bin/sh
set -eu
APP_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
DOTNET=${DOTNET:-dotnet}
export DOTNET_CLI_TELEMETRY_OPTOUT=1
OUT="$APP_ROOT/build/comparison"
mkdir -p "$OUT"
while IFS='|' read -r slug package version target; do
    project="$APP_ROOT/comparison/$slug/Reference.csproj"
    "$DOTNET" restore "$project" \
        --configfile "$APP_ROOT/comparison/NuGet.Config" \
        --disable-parallel --verbosity normal > "$OUT/$slug-restore.log"
    "$DOTNET" list "$project" package --include-transitive --format json \
        > "$OUT/$slug-native.json"
    "$DOTNET" nuget why "$project" "$target" --framework net8.0 \
        > "$OUT/$slug-native-tree.txt"
    PYTHONPATH="$APP_ROOT/src" "${PYTHON:-python3}" - \
        "$APP_ROOT" "$slug" "$package" "$version" <<'PY'
import json
import sys
from pathlib import Path
from depsview.repository import NuGetRepository
from depsview.graph import build_graph, load_order
from depsview.visualize import ascii_tree, render_svg
root, slug, package, version = sys.argv[1:]
root = Path(root)
out = root / 'build' / 'comparison'
repo = NuGetRepository('https://api.nuget.org/v3/index.json', 'net8.0')
start = repo.resolve(package, f'[{version}]')
graph = build_graph(repo, start)
render_svg(graph, out / f'{slug}.svg', start)
(out / f'{slug}-ascii.txt').write_text(ascii_tree(graph, start))
(out / f'{slug}-order.txt').write_text('\n'.join(map(str, load_order(
    graph, start))))
assets = root / 'comparison' / slug / 'obj' / 'project.assets.json'
native = json.loads(assets.read_text())['libraries']
official = {n.lower().replace('/', '@') for n, item in native.items()
            if item['type'] == 'package'}
own = {str(node).lower() for node in graph}
result = {'package': package, 'own': len(own), 'dotnet': len(official),
          'only_own': sorted(own - official),
          'only_dotnet': sorted(official - own)}
(out / f'{slug}-comparison.json').write_text(json.dumps(result, indent=2))
assert own == official, result
print(f'{package}: {len(own)} пакетов, состав и версии совпали')
PY
done <<'SAMPLES'
serilog|Serilog.Sinks.Console|6.0.0|Serilog
configuration|Microsoft.Extensions.Configuration.Json|8.0.0|System.Text.Encodings.Web
logging|Microsoft.Extensions.Logging.Console|8.0.0|Microsoft.Extensions.Primitives
SAMPLES
