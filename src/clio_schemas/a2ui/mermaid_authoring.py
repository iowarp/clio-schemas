"""Capability-complete authoring annotation for the Mermaid component lookup.

The index stays short. The component's JSON Schema carries this non-validating
annotation so one deep lookup returns the host contract and source-language guide.
Examples are executable inputs, checked against the consumer's pinned renderer.
"""

from __future__ import annotations

from typing import Any


def _family(
    family: str, declarations: list[str], use: str, syntax: str, source: str
) -> dict[str, Any]:
    return {
        "family": family,
        "declarations": declarations,
        "use": use,
        "syntax": syntax,
        "example": source,
    }


MERMAID_AUTHORING: dict[str, Any] = {
    "renderer": {"package": "pele", "version": "1.6.0"},
    "scope": (
        "Complete family inventory for CLIO's bundled Pele 1.6.0. These are source "
        "declarations inside the existing Mermaid component, not component names. "
        "Each family has a working starting example and its authoring operators. "
        "The examples are synthetic, not measurements. Adapt relationships and "
        "labels to the actual evidence; there is no required diagram or panel set."
    ),
    "host": [
        "Use source OR dataUri, never both. dataUri uses the actual returned artifact URI "
        "of a registered UTF-8 source file. Where the producer accepts a workspace "
        "file path, it registers that file before validation; reuse its returned URI. "
        "Do not guess artifact IDs or use HTTP URLs. "
        "source can be a dynamic string binding; the bound value is diagram text.",
        "A mermaid fenced block uses the same diagram language for an inline explanation. "
        "Use the declared dashboard tools for a saved composed report. Do not install "
        "Pele, import JavaScript, or invent clio.pele.v1.",
        "CLIO supplies theme colours and adaptive container width. Renderer options "
        "maxWidth, responsive, config, themeVariables and custom CSS are not component "
        "properties. Mermaid init directives, HTML labels, arbitrary callbacks and "
        "external images/links are rejected. Text line breaks use literal backslash-n "
        "inside labels (encoded as \\\\n in JSON); source statements use JSON \\n.",
        "Navigation: add a standalone flowchart line: click data "
        '"workspace-folder:data/inputs" "Open inputs". data must be an existing '
        "node; the relative directory must exist in the current workspace. Encode "
        "reserved path characters. The host opens Files using existing access. "
        "This does not run code, create a folder, or grant permissions. Plain exports "
        "do not provide workspace navigation.",
        "The component has source view, zoom, pan, expand, copy, SVG/PNG/source export "
        "and selection/reference controls supplied by the viewer. Do not add fake "
        "toolbar properties. Tree filenames, architecture services and git commits "
        "are diagram text; they do not automatically become file navigation.",
        "Preserve semantics before styling: branch conditions, message order, entity "
        "cardinality, grammar repetition and hierarchy are different relationships. "
        "Use clio.chart.v1 for data-backed quantitative views needing units, filters "
        "or shared selection; Mermaid chart families remain available for small "
        "self-contained illustrations. Use graph views for exploratory node networks.",
        "Review the actual published artifact: inspect its captured image at the "
        "docked width and expanded when useful, including titles, text, arrows and "
        "legends. Fix clipping, tiny text, lost edges or misleading relationships "
        "and capture again. A valid schema, accepted source or SVG is not a visual "
        "pass. If capture is unavailable, report that specific gap. The shared "
        "review-visual-presentation skill supplies the capture workflow.",
        "On an error, repair the actual declaration, quoting, indentation, block "
        "endings or operators; preserve difficult relationships. CLIO can fall back "
        "to Mermaid for legacy syntax, but Pele-only declarations need Pele. Do not "
        "silently replace the diagram with an unrelated gallery. External Mermaid "
        "plugins such as ZenUML and custom icon resolvers are not exposed.",
    ],
    "source_encoding": {
        "rule": "The source value contains actual line breaks between statements. "
        "JSON encodes each newline once as \\n. Do not double-escape them as \\\\n, "
        "which leaves backslash and n characters in the source. When writing JSON "
        "from Python/JavaScript, construct a multiline source string and serialize "
        "the document once. Label-internal backslash-n is a different syntax.",
        "component_example": {
            "id": "process",
            "component": "clio.mermaid.v1",
            "title": "Review decision",
            "source": (
                "flowchart LR\n  input[Input] --> check{Valid?}\n"
                "  check -->|Yes| save[Save]\n  check -->|No| repair[Repair]"
            ),
        },
    },
    "families": [
        _family(
            "flowchart",
            ["flowchart", "graph"],
            "Directed stages, dependencies and decisions.",
            "LR/RL/TB/BT set direction. id[Label], id{Decision}, --> edges, "
            "-->|condition| labelled edges; subgraph id[Label] ... end groups nodes. "
            "Stable IDs differ from display labels. classDef/class can mark semantic categories.",
            (
                "flowchart LR\n  raw[Raw input] --> check{Valid?}\n  check -->|Yes| "
                "save[Save]\n  check -->|No| repair[Repair]\n  repair --> check"
            ),
        ),
        _family(
            "sequence",
            ["sequenceDiagram"],
            "Ordered exchanges between participants.",
            "actor/participant name lifelines; ->> sends and -->> replies. "
            "alt condition / else condition / end is exclusive; opt, loop, par and "
            "critical blocks also end with end. activate/deactivate and Note over "
            "are available. A request and reply are separate messages.",
            (
                "sequenceDiagram\n  actor Reader\n  participant API\n  Reader->>API: "
                "Request\n  alt Allowed\n    API-->>Reader: Record\n  else Denied\n    "
                "API-->>Reader: Error\n  end"
            ),
        ),
        _family(
            "class",
            ["classDiagram"],
            "Types, members, inheritance and composition.",
            "class Name { type field; method() } uses one member per line. "
            "<|-- inheritance, *-- composition, o-- aggregation, --> association; "
            "quoted multiplicities precede relation ends. + public, - private.",
            (
                "classDiagram\n  class Sensor {\n    +string id\n    +read()\n  }\n  "
                'class Recorder\n  Recorder "1" o-- "1..*" Sensor : reads'
            ),
        ),
        _family(
            "state",
            ["stateDiagram", "stateDiagram-v2"],
            "Lifecycle states and transitions.",
            "[*] is entry/exit; A --> B : trigger. state Label as ID gives aliases. "
            "Composite state ID { ... } nests transitions; <<choice>>, <<fork>>, "
            "<<join>> express branching. Do not confuse states with actions.",
            (
                "stateDiagram-v2\n  [*] --> Idle\n  Idle --> Running : start\n  "
                "Running --> Failed : error\n  Failed --> Running : retry\n  Running "
                "--> Complete : success\n  Complete --> [*]"
            ),
        ),
        _family(
            "er",
            ["erDiagram"],
            "Entities, attributes and cardinality.",
            "Entity { type name PK/FK } lists attributes. || exactly one, o| zero "
            "or one, }o/o{ zero or many, }|/|{ one or many. -- identifying, .. "
            "non-identifying; read the marker at each entity end independently. "
            "If an attribute type is not supplied, use an unspecified placeholder "
            "and explain it. Do not infer primary/foreign keys from names or add "
            "attributes to make an entity box look complete. Retain unknowns as unknowns.",
            (
                "erDiagram\n  STATION ||--o{ OBSERVATION : has\n  STATION {\n    "
                "string station_id PK\n  }\n  OBSERVATION {\n    int observation_id PK"
                "\n    string station_id FK\n  }"
            ),
        ),
        _family(
            "gantt",
            ["gantt"],
            "Dated work, durations and dependencies.",
            "dateFormat controls input dates; section groups rows. Task :id,start,duration; "
            "after id starts after a dependency. done, active, crit and milestone are task tags. "
            "Use real dates/durations or label them illustrative.",
            (
                "gantt\n  dateFormat YYYY-MM-DD\n  section Trial\n  Collect :a, "
                "2026-10-01, 2d\n  Analyse :b, after a, 3d"
            ),
        ),
        _family(
            "gitGraph",
            ["gitGraph"],
            "Commit ancestry, branch histories and merges.",
            'commit id: "label" creates a commit on the active branch. branch name '
            "creates/switches a branch; checkout name switches; merge name merges it "
            "into the active branch. cherry-pick id: copies a commit; tag/type are "
            "commit options. Preserve branching points, not just labels.",
            (
                'gitGraph\n  commit id: "A"\n  branch trial\n  commit id: "B"\n  '
                'checkout main\n  commit id: "C"\n  merge trial id: "M"'
            ),
        ),
        _family(
            "mindmap",
            ["mindmap"],
            "A conceptual hierarchy.",
            "Indentation determines parent/child structure. root((Label)) is a root "
            "shape; children may use [rectangle], (rounded), {{hexagon}}. Equal "
            "indentation means siblings; do not use it for message order.",
            (
                "mindmap\n  root((Study))\n    Inputs\n      Samples\n      Metadata"
                "\n    Outputs\n      Report"
            ),
        ),
        _family(
            "timeline",
            ["timeline"],
            "Events grouped by period.",
            "title names the view; section groups periods. Period : event : another "
            "event associates events with a period. A following : event extends it.",
            "timeline\n  title Trial history\n  2025 : Pilot\n  2026 : Replication : Review",
        ),
        _family(
            "journey",
            ["journey"],
            "A person's experience across tasks.",
            "section groups stages. Task: score: Actor, OtherActor gives a 1–5 "
            "experience score and responsible actors. Scores are not measured timings.",
            (
                "journey\n  title Review experience\n  section Evidence\n    Find "
                "source: 3: Analyst\n    Inspect result: 5: Analyst, Reviewer"
            ),
        ),
        _family(
            "pie",
            ["pie"],
            "A small part-to-whole illustration.",
            'pie title ... followed by "Category" : numericValue; showData shows values. '
            "Keep original units and denominators clear; use charts for linked data.",
            'pie title Synthetic allocation\n  "Analysis" : 60\n  "Review" : 40',
        ),
        _family(
            "quadrantChart",
            ["quadrantChart"],
            "Items positioned on two qualitative axes.",
            "x-axis Low --> High and y-axis Low --> High label axes; quadrant-1..4 "
            "label regions. Item: [x,y] places a point with coordinates in [0,1].",
            (
                "quadrantChart\n  x-axis Low effort --> High effort\n  y-axis Low "
                "value --> High value\n  quadrant-1 Plan\n  quadrant-2 Prioritise\n  "
                "quadrant-3 Defer\n  quadrant-4 Reconsider\n  Trial: [0.3, 0.8]"
            ),
        ),
        _family(
            "xychart",
            ["xychart", "xychart-beta"],
            "Small numeric bar/line illustrations.",
            "x-axis [categories] or a numeric range; y-axis title min --> max; "
            "bar [values] and line [values]. Array positions must match x values.",
            'xychart-beta\n  x-axis [A, B, C]\n  y-axis "Count" 0 --> 10\n  bar [3, 7, 5]',
        ),
        _family(
            "requirement",
            ["requirementDiagram"],
            "Requirements, risks, verification and traceability.",
            "requirement ID { id: ...; text: ...; risk: low/medium/high; "
            "verifymethod: test/analysis/inspection/demonstration } uses separate lines. "
            "element ID { type: ... } names evidence/system elements. "
            "A - satisfies -> B (also verifies, traces, refines, contains, copies, derives).",
            (
                "requirementDiagram\n  requirement r1 {\n    id: R1\n    text: "
                "Preserve units\n    risk: medium\n    verifymethod: test\n  }\n  "
                'element checker {\n    type: "test"\n  }\n  checker - verifies -> r1'
            ),
        ),
        _family(
            "sankey",
            ["sankey", "sankey-beta"],
            "Weighted flows between categories.",
            "After the declaration, CSV rows are source,target,value. Quote names "
            "containing commas. Edge width represents the numeric value; use consistent units.",
            "sankey-beta\nInput,Accepted,8\nInput,Rejected,2\nAccepted,Report,8",
        ),
        _family(
            "architecture",
            ["architecture-beta"],
            "Services, groups, ports and connections.",
            "group id(icon)[Label]; service id(icon)[Label] in groupId. "
            "Built-in icons include cloud, database, disk, server, internet. "
            "a:R -- L:b connects right/left ports; :T/:B top/bottom; arrows add direction. "
            "These symbols are not connections to real services.",
            (
                "architecture-beta\n  group lab(cloud)[Lab]\n  service "
                "api(server)[API] in lab\n  service db(database)[Store] in lab\n  "
                "api:R -- L:db"
            ),
        ),
        _family(
            "c4",
            ["C4Context", "C4Container", "C4Component", "C4Dynamic", "C4Deployment"],
            "Architecture at a declared level of abstraction.",
            'Person(id,"Label"), System(id,"Label"), Container(id,"Label","Tech"), '
            'Component(id,"Label","Tech"), Rel(a,b,"Purpose"). Boundaries use braces. '
            "C4Dynamic uses ordered Rel calls; Deployment_Node contains Container instances. "
            "Do not mix context systems with deployment nodes without explaining the level.",
            (
                'C4Context\n  Person(reader, "Reader")\n  System(catalog, "Catalog")'
                '\n  Rel(reader, catalog, "Finds evidence")'
            ),
        ),
        _family(
            "block",
            ["block", "block-beta"],
            "Explicitly arranged blocks and connections.",
            "columns N sets columns; id[Label]:span spans columns; space reserves a "
            "cell. block:group ... end nests blocks; A --> B adds relationships. "
            "Use this when explicit grouping matters more than automatic graph layout.",
            (
                'block-beta\n  columns 2\n  a["Acquire"] b["Analyse"]\n  c["Review"]:2'
                "\n  a --> c\n  b --> c"
            ),
        ),
        _family(
            "packet",
            ["packet", "packet-beta"],
            "Bit/field structure of a packet.",
            'start-end: "Field" assigns an inclusive bit range; +N: "Field" appends '
            "N bits. Preserve field widths and ordering. It does not model message exchanges.",
            'packet-beta\n  0-3: "Version"\n  4-7: "Flags"\n  8-15: "Length"',
        ),
        _family(
            "kanban",
            ["kanban"],
            "Work items grouped by status.",
            "ColumnID[Column label] at one indent, cardID[Card label] beneath it. "
            "Card metadata can set assigned, ticket and priority. It illustrates "
            "state; it does not create CLIO tasks or make cards a live task board.",
            (
                "kanban\n  todo[To do]\n    clean[Clean samples]\n  done[Done]\n    "
                "collect[Collect samples]"
            ),
        ),
        _family(
            "radar",
            ["radar-beta"],
            "Series compared over named axes.",
            'axis id1["Label"], id2["Label"]; curve series["Label"]{values}; max N sets '
            "the scale. Values follow axis order. Do not invent normalized scores.",
            (
                'radar-beta\n  axis q["Quality"], s["Speed"], c["Coverage"]\n  curve '
                'a["Trial A"]{8, 4, 6}\n  max 10'
            ),
        ),
        _family(
            "treemap",
            ["treemap", "treemap-beta"],
            "A weighted hierarchy of categories.",
            'Indent "Group" headings and "Leaf": value children. Area represents '
            "the numeric weight, not temporal order; preserve the hierarchy and units.",
            'treemap-beta\n  "Work"\n    "Analysis": 6\n    "Review": 4',
        ),
        _family(
            "railroad",
            ["railroad-beta", "railroad-ebnf-beta", "railroad-abnf-beta", "railroad-peg-beta"],
            "Accepted token sequences in a grammar.",
            "Choose one notation. EBNF: name = expression ;, quoted terminals, "
            "bare rule references, adjacency sequence, | choice, [x] optional, "
            "(x) grouping, x* zero-or-more, x+ one-or-more. ABNF: name = expression, "
            "/ choice, [x] optional, *x zero-or-more, 1*x one-or-more, %x41 hex terminal. "
            "PEG: name <- expression ;, / ordered choice, x? optional, x* and x+ "
            "repetition, &x/!x lookahead; quote terminals. End productions with ; "
            "in each notation in this renderer. The railroad DSL uses "
            'name = terminal("word") ; with nonterminal("rule"), sequence(...), '
            "choice(...), optional(...), zeroOrMore(...) and oneOrMore(...). "
            "Do not mix operators; define referenced rules and preserve optionality.",
            (
                'railroad-ebnf-beta\nrequest = "READ" names [ "WHERE" name ] ;\nnames'
                ' = name ( "," name )* ;\nname = ( "a" | "b" | "c" )+ ;'
            ),
        ),
        _family(
            "agentflow",
            ["agentflow-beta"],
            "Agent actions, tools, inputs and reference documents.",
            "Flowchart-like direction, nodes and edges, with semantic shapes "
            "@{ type: input/tool/action/refdoc/decision/task }. --> is sequence; "
            "reference/failure links have different meaning. This is a diagram, "
            "not an agent execution or task submission mechanism.",
            (
                'agentflow-beta LR\n  input@{ type: input, label: "Question" }\n  '
                'step@{ type: action, label: "Review" }\n  input --> step'
            ),
        ),
        _family(
            "treeView",
            ["treeView-beta"],
            "Directory/file trees.",
            "Indent children beneath parents; a trailing / denotes a directory. "
            "A file has no trailing /. ## description annotates an entry. "
            "Preserve names/extensions; displaying a file does not grant/open it.",
            "treeView-beta\n  study/\n    data/\n      readings.csv\n    report.md",
        ),
        _family(
            "cynefin",
            ["cynefin-beta"],
            "Classify decisions by the Cynefin domains.",
            'complex/complicated/clear/chaotic/confusion headings with indented "Item" labels. '
            "domain --> domain : label marks a transition. Domains express the "
            "decision context, not measured risk scores.",
            'cynefin-beta\n  complex\n    "Explore hypothesis"\n  clear\n    "Apply checklist"',
        ),
        _family(
            "wardley",
            ["wardley-beta"],
            "Value-chain dependencies and evolution.",
            "anchor Name [visibility,evolution]; component Name [visibility,evolution]; "
            "A -> B is a dependency; evolve Name target proposes evolution. "
            "Coordinates are in [0,1]; label hypothetical positions as estimates.",
            (
                "wardley-beta\n  anchor Reader [0.95, 0.5]\n  component Report [0.8, "
                "0.6]\n  component Storage [0.2, 0.85]\n  Reader -> Report\n  Report "
                "-> Storage"
            ),
        ),
        _family(
            "eventmodeling",
            ["eventmodeling"],
            "Commands, events and read models over chronological frames.",
            "tf frame kind Name defines a frame; kinds ui, cmd, evt, rmo, pcr "
            "identify user interface, command, event, read model, processor. "
            "[[dataName]] references a data block. Frame order is chronology, "
            "not a generic causal arrow between arbitrary nodes.",
            (
                "eventmodeling\n  tf 01 ui ReviewUI\n  tf 02 cmd SubmitReview\n  tf 03"
                " evt ReviewSubmitted\n  tf 04 rmo ReviewList"
            ),
        ),
        _family(
            "usecase",
            ["usecase-beta"],
            "Actors and goals within a system boundary.",
            'actor id("Label"), goal("Label"); systemBoundary id[Label] ... end groups '
            "goals. actor --> goal associates them. include/extend relate use "
            "cases; inheritance is different from a sequential workflow.",
            (
                'usecase-beta\n  actor reader("Reader")\n  inspect("Inspect '
                'evidence")\n  reader --> inspect'
            ),
        ),
        _family(
            "venn",
            ["venn-beta"],
            "Set sizes and intersections.",
            "set A[Label]:size; set B[Label]:size; union A,B:overlap describes an "
            "intersection. Use consistent counts and feasible intersections, "
            "not arbitrary decorative circle sizes.",
            "venn-beta\n  set A[Reviewed]:8\n  set B[Published]:6\n  union A,B:3",
        ),
        _family(
            "ishikawa",
            ["ishikawa", "ishikawa-beta"],
            "Possible causes of an effect.",
            "An effect heading and indented category/cause hierarchy forms the "
            "fishbone. Categories group hypotheses, not proven causation. "
            "Keep evidence-backed causes distinguishable from suggestions.",
            (
                "ishikawa-beta\n  Missing records\n    Inputs\n      Late arrival\n"
                "      Invalid format"
            ),
        ),
        _family(
            "swimlane",
            ["swimlane-beta"],
            "Workflow grouped by responsible actor/team.",
            "LR or TB selects direction; subgraph actor[Actor] ... end creates "
            "a lane; ordinary flowchart nodes/arrows connect actions across lanes. "
            "Lane ownership is distinct from a sequence diagram lifeline.",
            (
                "swimlane-beta LR\n  subgraph analyst[Analyst]\n    submit[Submit]\n  "
                "end\n  subgraph reviewer[Reviewer]\n    inspect[Inspect]\n  end\n  "
                "submit --> inspect"
            ),
        ),
        _family(
            "info",
            ["info"],
            "Renderer diagnostic information.",
            "The declaration alone renders version/diagnostic information. "
            "Use only when diagnosing the viewer, not as a diagram of user data.",
            "info",
        ),
    ],
    "notation_variants": {
        "railroad-beta": (
            'railroad-beta\nrequest = sequence(terminal("READ"), optional(terminal("ALL"))) ;'
        ),
        "railroad-abnf-beta": (
            'railroad-abnf-beta\nrequest = "READ" 1*letter [" ALL"] ;\nletter = "a" / "b" / "c" ;'
        ),
        "railroad-peg-beta": (
            'railroad-peg-beta\nrequest <- "READ" letter+ "ALL"? ;\nletter <- "a" / "b" / "c" ;'
        ),
        "C4Container": (
            'C4Container\n  Person(reader, "Reader")\n  Container(api, "API", '
            '"Python")\n  ContainerDb(db, "Records", "SQL")\n  Rel(reader, api, '
            '"Queries")\n  Rel(api, db, "Reads")'
        ),
        "C4Component": (
            'C4Component\n  Component(api, "API", "HTTP")\n  Component(store, '
            '"Repository", "Python")\n  Rel(api, store, "Reads records")'
        ),
        "C4Dynamic": (
            'C4Dynamic\n  Person(reader, "Reader")\n  Container(api, "API", '
            '"HTTP")\n  Rel(reader, api, "Requests record")'
        ),
        "C4Deployment": (
            'C4Deployment\n  Deployment_Node(host, "Host", "Linux") {\n    '
            'Container(api, "API", "Python")\n  }'
        ),
    },
    "references": {
        "upstream": "https://pele.run/compatibility",
        "syntax_examples": "https://pele.run/examples",
        "version_rule": "This inventory follows the pinned consumer, not the latest website. "
        "New library versions require a fresh coverage and rendering check.",
    },
}
