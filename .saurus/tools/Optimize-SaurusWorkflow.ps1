[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$RepoRoot,

    [string]$Workflow = ""
)

Set-StrictMode -Version 2.0
$ErrorActionPreference = "Stop"

function Resolve-SaurusWorkflow {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Root,

        [string]$RequestedWorkflow
    )

    if (-not [string]::IsNullOrWhiteSpace($RequestedWorkflow)) {
        $candidate = if ([System.IO.Path]::IsPathRooted($RequestedWorkflow)) {
            $RequestedWorkflow
        }
        else {
            Join-Path $Root $RequestedWorkflow
        }

        if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) {
            throw "Workflow nao encontrado: $candidate"
        }

        return (Resolve-Path -LiteralPath $candidate).Path
    }

    $workflowDirectory = Join-Path $Root ".github\workflows"
    if (-not (Test-Path -LiteralPath $workflowDirectory -PathType Container)) {
        throw "Pasta de workflows nao encontrada: $workflowDirectory"
    }

    $candidates = @(
        Get-ChildItem -LiteralPath $workflowDirectory -File |
            Where-Object { $_.Name -match '^build-saurus-remote-windows.*\.ya?ml$' } |
            Sort-Object Name
    )

    if ($candidates.Count -eq 0) {
        throw "Nenhum workflow build-saurus-remote-windows*.yml ou .yaml foi encontrado."
    }

    $preferred = @($candidates | Where-Object { $_.Name -like '*3.1.2*' })
    if ($preferred.Count -gt 0) {
        return $preferred[-1].FullName
    }

    return $candidates[-1].FullName
}

function Insert-BeforeMarker {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Text,

        [Parameter(Mandatory = $true)]
        [string]$Marker,

        [Parameter(Mandatory = $true)]
        [string]$Content,

        [Parameter(Mandatory = $true)]
        [string]$Description
    )

    $position = $Text.IndexOf($Marker, [System.StringComparison]::Ordinal)
    if ($position -lt 0) {
        throw "${Description}: marcador nao encontrado."
    }

    return $Text.Insert($position, $Content)
}

$root = (Resolve-Path -LiteralPath $RepoRoot).Path
$workflowPath = Resolve-SaurusWorkflow -Root $root -RequestedWorkflow $Workflow
$text = [System.IO.File]::ReadAllText($workflowPath)
$text = $text.Replace("`r`n", "`n")

if (-not $text.Contains("group: saurus-remote-windows-x64")) {
    $permissionsPattern = '(?m)^permissions:\s*\n\s+contents:\s+read\s*\n'
    $permissionsRegex = [System.Text.RegularExpressions.Regex]::new($permissionsPattern)
    $permissionMatches = $permissionsRegex.Matches($text)
    if ($permissionMatches.Count -ne 1) {
        throw "Nao foi possivel inserir o bloco de concorrencia: esperado 1 bloco permissions/contents, encontrado $($permissionMatches.Count)."
    }

    $replacement = @(
        "permissions:",
        "  contents: read",
        "",
        "# Avoid spending runner minutes on an obsolete manual build of the same label.",
        "concurrency:",
        '  group: saurus-remote-windows-x64-${{ github.ref }}-${{ inputs.build_label }}',
        "  cancel-in-progress: true",
        ""
    ) -join "`n"

    $text = $permissionsRegex.Replace($text, $replacement, 1)
}

$text = $text.Replace("fetch-depth: 0", "fetch-depth: 1")

if (-not $text.Contains("Apply Saurus UX refresh")) {
    $marker = "      - name: Verify Saurus customization and secret policy`n"
    $step = @(
        "      - name: Apply Saurus UX refresh",
        "        shell: pwsh",
        "        run: |",
        '          python .\.saurus\tests\test_ux_refresh.py',
        '          if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }',
        '          python .\.saurus\tools\apply_saurus_ux_refresh.py --source-root .',
        '          if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }',
        "",
        ""
    ) -join "`n"

    $text = Insert-BeforeMarker -Text $text -Marker $marker -Content $step -Description "Etapa existente de verificacao Saurus"
}

if (-not $text.Contains("Verify Saurus UX refresh")) {
    $marker = "      - name: Restore generated Flutter-Rust bridge`n"
    $step = @(
        "      - name: Verify Saurus UX refresh",
        "        shell: pwsh",
        "        run: |",
        '          python .\.saurus\tools\verify_saurus_ux_refresh.py --source-root .',
        '          if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }',
        "",
        ""
    ) -join "`n"

    $text = Insert-BeforeMarker -Text $text -Marker $marker -Content $step -Description "Etapa de restauracao da bridge"
}

$flutterPattern = '(?ms)^      - name: Install Flutter\n(?:(?!^      - name:).)*?^          architecture: x64\n'
$flutterRegex = [System.Text.RegularExpressions.Regex]::new($flutterPattern)
$flutterMatch = $flutterRegex.Match($text)
if ($flutterMatch.Success) {
    $architectureLine = "          architecture: x64`n"
    $architectureCount = ([System.Text.RegularExpressions.Regex]::Matches(
        $flutterMatch.Value,
        [System.Text.RegularExpressions.Regex]::Escape($architectureLine)
    )).Count

    if ($architectureCount -ne 1) {
        throw "Nao foi possivel habilitar o cache do Flutter de forma segura."
    }

    $updatedBlock = $flutterMatch.Value.Replace("          cache: true`n", "")
    if (-not $updatedBlock.Contains("pub-cache: true")) {
        $updatedBlock = $updatedBlock.Replace(
            $architectureLine,
            "          architecture: x64`n          pub-cache: true`n"
        )
    }

    $text = $text.Substring(0, $flutterMatch.Index) +
        $updatedBlock +
        $text.Substring($flutterMatch.Index + $flutterMatch.Length)
}

$text = $text.Replace("          flutter doctor -v`n", "          flutter --version`n")

if (-not $text.Contains("Format refreshed Flutter sources")) {
    $marker = "      - name: Install Rust toolchain`n"
    $step = @(
        "      - name: Format refreshed Flutter sources",
        "        shell: pwsh",
        "        run: |",
        '          dart format .\flutter\lib\desktop\pages\desktop_home_page.dart .\flutter\lib\desktop\pages\connection_page.dart',
        '          if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }',
        '          python .\.saurus\tools\verify_saurus_ux_refresh.py --source-root .',
        '          if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }',
        "",
        ""
    ) -join "`n"

    $text = Insert-BeforeMarker -Text $text -Marker $marker -Content $step -Description "Etapa de instalacao do Rust"
}

$requiredMarkers = @(
    "Apply Saurus UX refresh",
    "Verify Saurus UX refresh",
    "Format refreshed Flutter sources"
)
foreach ($requiredMarker in $requiredMarkers) {
    if (-not $text.Contains($requiredMarker)) {
        throw "Validacao final falhou: etapa ausente '$requiredMarker'."
    }
}

if (-not $text.EndsWith("`n")) {
    $text += "`n"
}

$utf8WithoutBom = [System.Text.UTF8Encoding]::new($false)
[System.IO.File]::WriteAllText($workflowPath, $text, $utf8WithoutBom)

$relativePath = $workflowPath
if ($workflowPath.StartsWith($root, [System.StringComparison]::OrdinalIgnoreCase)) {
    $relativePath = $workflowPath.Substring($root.Length).TrimStart([char[]]"\/")
}

Write-Host "[OK] Workflow otimizado: $relativePath" -ForegroundColor Green
