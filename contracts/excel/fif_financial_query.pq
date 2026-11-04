// FIF financial query — Power Query M template (Option A).
// Replace every <<PLACEHOLDER>>. Do not store real tokens, hosts, or entity ids.
// Target: POST /api/forensics/v1/financial/query (JSON). Refresh is Data → Refresh All.

let
    Url = "<<FIF_QUERY_URL>>",
    BearerToken = "<<FIF_BEARER_TOKEN>>",
    RequestJson = "<<FIF_REQUEST_JSON>>",
    ResponseBytes = Web.Contents(
        Url,
        [
            Headers = [
                Authorization = "Bearer " & BearerToken,
                #"Content-Type" = "application/json",
                Accept = "application/json"
            ],
            Content = Text.ToBinary(RequestJson),
            ManualStatusHandling = {401, 402, 403, 404, 405, 413, 503}
        ]
    ),
    Document = Json.Document(ResponseBytes),
    Receipt = Document[receipt],
    Nodes = Receipt[nodes],
    NodesTable = Table.FromList(Nodes, Splitter.SplitByNothing(), {"node"}),
    Expanded = Table.ExpandRecordColumn(
        NodesTable,
        "node",
        Record.FieldNames(Nodes{0})
    )
in
    Expanded
