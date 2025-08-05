"""
M-Query Templates with Built-in Error Handling
These templates ensure all generated M-Query code is resilient to failures
"""

# Template for SQL Database connections
SQL_DATABASE_TEMPLATE = """
let
    // Connection with comprehensive error handling
    ConnectionAttempt = try 
        Sql.Database("{{server}}", "{{database}}"{{#if connection_options}}, {{connection_options}}{{/if}})
    otherwise 
        error [
            Reason = "DatabaseConnectionFailed",
            Message = "Failed to connect to {{server}}.{{database}}",
            Detail = "Please check server name, credentials, and network connectivity"
        ],
    
    // Get data with error handling
    DataAttempt = if ConnectionAttempt[HasError] then
        ConnectionAttempt
    else
        try
            let
                Source = ConnectionAttempt[Value],
                {{#if schema}}Schema = Source{[Schema="{{schema}}"]}[Data],{{/if}}
                {{#if table_name}}
                TableData = {{#if schema}}Schema{{else}}Source{{/if}}{[Name="{{table_name}}"]}[Data]
                {{else if sql_query}}
                TableData = Value.NativeQuery(Source, "{{sql_query}}")
                {{else}}
                TableData = Source
                {{/if}}
            in
                TableData
        otherwise
            error [
                Reason = "DataRetrievalFailed", 
                Message = "Failed to retrieve data from {{table_name}}",
                Detail = "Table might not exist or query syntax error"
            ],
    
    // Create result with fallback
    Result = if DataAttempt[HasError] then
        let
            // Create empty table with expected schema
            EmptyTable = Table.FromColumns(
                { {{#each columns}}{} {{#unless @last}}, {{/unless}}{{/each}} },
                { {{#each columns}}"{{name}}"{{#unless @last}}, {{/unless}}{{/each}} }
            ),
            // Add error information
            WithErrorInfo = Table.AddColumn(
                EmptyTable,
                "_ErrorInfo",
                each Text.Combine({
                    "Error: ",
                    try Text.From(DataAttempt[Error][Message]) otherwise "Unknown error",
                    " (", 
                    try Text.From(DataAttempt[Error][Reason]) otherwise "Unknown reason",
                    ")"
                })
            )
        in
            WithErrorInfo
    else
        DataAttempt[Value],
    
    // Apply type conversions with error handling
    TypedResult = try
        Table.TransformColumnTypes(Result, {
            {{#each columns}}
            {"{{name}}", {{powerbi_type}}}{{#unless @last}},{{/unless}}
            {{/each}}
        })
    otherwise
        Result  // Return untyped if conversion fails
in
    TypedResult
"""

# Template for CSV/File connections
FILE_SOURCE_TEMPLATE = """
let
    // File access with error handling
    SourceAttempt = try
        {{#if file_type_csv}}
        Csv.Document(File.Contents("{{file_path}}"), [
            Delimiter = "{{delimiter}}",
            Encoding = {{encoding}},
            QuoteStyle = QuoteStyle.{{quote_style}}
        ])
        {{else if file_type_excel}}
        Excel.Workbook(File.Contents("{{file_path}}"), null, true)
        {{else}}
        File.Contents("{{file_path}}")
        {{/if}}
    otherwise
        error [
            Reason = "FileAccessFailed",
            Message = "Cannot access file: {{file_path}}",
            Detail = "File might not exist or access denied"
        ],
    
    // Process data with fallback
    ProcessedData = if SourceAttempt[HasError] then
        // Return empty table on error
        Table.FromColumns(
            { {{#each columns}}{} {{#unless @last}}, {{/unless}}{{/each}} },
            { {{#each columns}}"{{name}}"{{#unless @last}}, {{/unless}}{{/each}} }
        )
    else
        let
            Data = SourceAttempt[Value],
            {{#if promote_headers}}
            WithHeaders = Table.PromoteHeaders(Data),
            {{else}}
            WithHeaders = Data,
            {{/if}}
            // Type conversion with error handling
            Typed = try
                Table.TransformColumnTypes(WithHeaders, {
                    {{#each columns}}
                    {"{{name}}", {{powerbi_type}}}{{#unless @last}},{{/unless}}
                    {{/each}}
                })
            otherwise
                WithHeaders
        in
            Typed,
    
    // Add metadata about data source status
    FinalResult = if SourceAttempt[HasError] then
        Table.AddColumn(
            ProcessedData,
            "_SourceStatus",
            each "Error: " & Text.From(SourceAttempt[Error][Message])
        )
    else
        ProcessedData
in
    FinalResult
"""

# Template for Web/API connections
WEB_API_TEMPLATE = """
let
    // Web request with error handling and retry
    MakeRequest = (attempt as number) =>
        try
            Web.Contents("{{url}}", [
                Headers = [
                    {{#each headers}}
                    {{@key}} = "{{this}}"{{#unless @last}},{{/unless}}
                    {{/each}}
                ],
                {{#if is_post}}
                Content = Text.ToBinary("{{request_body}}"),
                {{/if}}
                Timeout = #duration(0, 0, 0, {{timeout_seconds}}),
                ManualStatusHandling = {400, 401, 403, 404, 500, 502, 503}
            ])
        otherwise
            if attempt < 3 then
                Function.InvokeAfter(
                    () => MakeRequest(attempt + 1),
                    #duration(0, 0, 0, attempt * 2)  // Exponential backoff
                )
            else
                error [
                    Reason = "WebRequestFailed",
                    Message = "Failed to fetch data from {{url}}",
                    Detail = "Maximum retry attempts exceeded"
                ],
    
    // Make initial request
    Response = MakeRequest(1),
    
    // Parse response with error handling
    ParsedData = if Response[HasError] then
        error Response[Error]
    else
        let
            ResponseMeta = Value.Metadata(Response[Value]),
            StatusCode = ResponseMeta[Response.Status],
            Content = Response[Value]
        in
            if StatusCode >= 200 and StatusCode < 300 then
                try
                    Json.Document(Content)
                otherwise
                    error [
                        Reason = "ParseError",
                        Message = "Failed to parse JSON response",
                        Detail = "Response might not be valid JSON"
                    ]
            else
                error [
                    Reason = "HTTPError",
                    Message = "HTTP " & Text.From(StatusCode),
                    Detail = "Server returned an error status"
                ],
    
    // Convert to table with fallback
    TableResult = if ParsedData[HasError] then
        Table.FromColumns(
            { {{#each columns}}{} {{#unless @last}}, {{/unless}}{{/each}} },
            { {{#each columns}}"{{name}}"{{#unless @last}}, {{/unless}}{{/each}} }
        )
    else
        try
            {{#if json_to_table_path}}
            Table.FromRecords(ParsedData[{{json_to_table_path}}])
            {{else}}
            Table.FromRecords(ParsedData)
            {{/if}}
        otherwise
            Table.FromColumns(
                { {{#each columns}}{} {{#unless @last}}, {{/unless}}{{/each}} },
                { {{#each columns}}"{{name}}"{{#unless @last}}, {{/unless}}{{/each}} }
            )
in
    TableResult
"""

# Template selector function
def get_error_handled_template(source_type: str) -> str:
    """Get appropriate template based on source type"""
    templates = {
        'sql': SQL_DATABASE_TEMPLATE,
        'csv': FILE_SOURCE_TEMPLATE,
        'excel': FILE_SOURCE_TEMPLATE,
        'file': FILE_SOURCE_TEMPLATE,
        'web': WEB_API_TEMPLATE,
        'api': WEB_API_TEMPLATE,
        'rest': WEB_API_TEMPLATE
    }
    return templates.get(source_type.lower(), SQL_DATABASE_TEMPLATE)