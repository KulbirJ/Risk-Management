# ============================================================
# Supply Chain Risk Assessment - E2E API Tests (PowerShell)
# ============================================================
# Usage:  .\e2e_supply_chain_test.ps1
# Requires: curl.exe (ships with Windows 10+)
# ============================================================

param(
    [string]$BASE = "http://localhost:8000",
    [switch]$UseAWS
)

if ($UseAWS) {
    $BASE = "https://oyxvwg62f7.execute-api.ca-west-1.amazonaws.com"
}

$TID   = "67636bd3-9846-4bde-806f-aea369fc9457"
$UID   = "0bc9d6a9-f342-452e-9297-ee33f44d4f84"
$pass  = 0; $fail = 0; $errors = @()
$TMP   = [System.IO.Path]::GetTempFileName()

# ── IDs created during tests (for cleanup) ──
$SC_ASSESS_ID = ""
$SC_VENDOR_ID = ""
$SC_DEP_ID    = ""

function Invoke-API {
    param(
        [string]$Name,
        [string]$Method = "GET",
        [string]$Url,
        [string]$Body = "",
        [int]$ExpectedCode = 200
    )
    $sep = "|||HTTPCODE|||"
    $curlArgs = @("-s", "-X", $Method, $Url,
        "-H", "X-Tenant-ID: $TID",
        "-H", "X-User-ID: $UID",
        "-w", "$sep%{http_code}")
    if ($Body) {
        [System.IO.File]::WriteAllText($TMP, $Body, [System.Text.Encoding]::UTF8)
        $curlArgs += @("-H", "Content-Type: application/json", "-d", "@$TMP")
    }
    $raw   = (& curl.exe @curlArgs 2>&1) -join ""
    $idx   = $raw.LastIndexOf($sep)
    if ($idx -ge 0) {
        $code     = $raw.Substring($idx + $sep.Length).Trim()
        $respBody = $raw.Substring(0, $idx).Trim()
    } else {
        $code = "000"; $respBody = $raw
    }

    $ok    = ($code -eq [string]$ExpectedCode)
    $icon  = if ($ok) { "PASS" } else { "FAIL" }
    $color = if ($ok) { "Green" } else { "Red" }
    Write-Host ("  [{0}] {1}  (expected {2}  got {3})" -f $icon, $Name, $ExpectedCode, $code) -ForegroundColor $color
    if (-not $ok) {
        $preview = if ($respBody.Length -gt 300) { $respBody.Substring(0,300) } else { $respBody }
        Write-Host "        BODY: $preview" -ForegroundColor Yellow
        $script:fail += 1
        $script:errors += "${Name}: got $code expected $ExpectedCode"
    } else {
        $script:pass += 1
    }
    return @{ code = $code; body = $respBody }
}

# ============================================================
Write-Host "`n========================================================" -ForegroundColor Cyan
Write-Host '  SUPPLY CHAIN RISK ASSESSMENT - E2E API TESTS' -ForegroundColor Cyan
Write-Host "  Target: $BASE" -ForegroundColor Cyan
Write-Host "========================================================`n"

# ============================================================
Write-Host '  BLOCK 1 - Assessment CRUD' -ForegroundColor White
Write-Host "  ────────────────────────────────────────────────"

# 1.1  List assessments (empty or populated - either is fine)
Invoke-API "GET /supply-chain/ (list)" `
    -Url "$BASE/api/v1/supply-chain/" | Out-Null

# 1.2  Create assessment
$body = @{
    title                  = "E2E SC Test $(Get-Date -Format 'HHmmss')"
    description            = "Automated test - supply chain module"
    scope                  = "All third-party libraries"
    industry_sector        = "technology"
    technology_sensitivity = "High"
    technology_function    = "Authentication middleware"
    data_classification    = "Confidential"
    cyber_defense_level    = "Medium"
    deployment_environment = "Cloud (AWS)"
} | ConvertTo-Json -Compress

$r = Invoke-API "POST /supply-chain/ (create)" `
    -Method POST -Url "$BASE/api/v1/supply-chain/" -Body $body -ExpectedCode 201
if ($r.code -eq "201") {
    $SC_ASSESS_ID = ($r.body | ConvertFrom-Json).id
    Write-Host "        created assessment: $SC_ASSESS_ID" -ForegroundColor Gray
}

# 1.3  Get single assessment
if ($SC_ASSESS_ID) {
    Invoke-API "GET /supply-chain/{id} (detail)" `
        -Url "$BASE/api/v1/supply-chain/$SC_ASSESS_ID" | Out-Null
}

# 1.4  Update assessment
if ($SC_ASSESS_ID) {
    $update = @{ description = "Updated by e2e test"; status = "in_review" } | ConvertTo-Json -Compress
    Invoke-API "PUT /supply-chain/{id} (update)" `
        -Method PUT -Url "$BASE/api/v1/supply-chain/$SC_ASSESS_ID" -Body $update | Out-Null
}

# 1.5  List with status filter
Invoke-API "GET /supply-chain/?status=in_review (filter)" `
    -Url "$BASE/api/v1/supply-chain/?status=in_review" | Out-Null

# 1.6  Get non-existent assessment → 404
Invoke-API "GET /supply-chain/{fake} (404)" `
    -Url "$BASE/api/v1/supply-chain/00000000-0000-0000-0000-000000000000" -ExpectedCode 404 | Out-Null


# ============================================================
Write-Host "`n  BLOCK 2 - Vendor CRUD [CCCS Step 2]" -ForegroundColor White
Write-Host "  ────────────────────────────────────────────────"

if ($SC_ASSESS_ID) {
    # 2.1  Create vendor
    $vBody = @{
        assessment_id            = $SC_ASSESS_ID
        name                     = "Acme Security Corp"
        website                  = "https://acme-sec.example.com"
        vendor_type              = "commercial"
        country_of_origin        = "Canada"
        foci_risk                = "Low"
        geopolitical_risk        = "Low"
        business_practices_risk  = "Medium"
        security_certifications  = @("ISO27001", "SOC2")
        data_protection_maturity = "High"
        vuln_mgmt_maturity       = "High"
        security_policies_maturity = "High"
    } | ConvertTo-Json -Compress

    $r = Invoke-API "POST .../vendors (create)" `
        -Method POST -Url "$BASE/api/v1/supply-chain/$SC_ASSESS_ID/vendors" -Body $vBody -ExpectedCode 201
    if ($r.code -eq "201") {
        $parsed = $r.body | ConvertFrom-Json
        $SC_VENDOR_ID = $parsed.id
        Write-Host "        vendor id : $SC_VENDOR_ID" -ForegroundColor Gray
        Write-Host "        confidence: $($parsed.supplier_confidence_level)  score: $($parsed.supplier_risk_score)" -ForegroundColor Gray
    }

    # 2.2  Create high-risk vendor
    $vBody2 = @{
        assessment_id            = $SC_ASSESS_ID
        name                     = "Shady Offshore Ltd"
        vendor_type              = "oss"
        country_of_origin        = "Unknown"
        foci_risk                = "High"
        geopolitical_risk        = "High"
        business_practices_risk  = "High"
        data_protection_maturity = "Low"
        vuln_mgmt_maturity       = "Low"
        security_policies_maturity = "Low"
    } | ConvertTo-Json -Compress

    $r2 = Invoke-API "POST .../vendors (high-risk)" `
        -Method POST -Url "$BASE/api/v1/supply-chain/$SC_ASSESS_ID/vendors" -Body $vBody2 -ExpectedCode 201
    if ($r2.code -eq "201") {
        $p2 = $r2.body | ConvertFrom-Json
        Write-Host "        high-risk vendor confidence: $($p2.supplier_confidence_level)  score: $($p2.supplier_risk_score)" -ForegroundColor Gray
    }

    # 2.3  List vendors
    Invoke-API "GET .../vendors (list)" `
        -Url "$BASE/api/v1/supply-chain/$SC_ASSESS_ID/vendors" | Out-Null

    # 2.4  Get single vendor
    if ($SC_VENDOR_ID) {
        Invoke-API "GET .../vendors/{id} (detail)" `
            -Url "$BASE/api/v1/supply-chain/$SC_ASSESS_ID/vendors/$SC_VENDOR_ID" | Out-Null
    }

    # 2.5  Update vendor
    if ($SC_VENDOR_ID) {
        $vUpdate = @{ foci_risk = "Medium"; notes = "Updated in e2e" } | ConvertTo-Json -Compress
        Invoke-API "PUT .../vendors/{id} (update)" `
            -Method PUT -Url "$BASE/api/v1/supply-chain/$SC_ASSESS_ID/vendors/$SC_VENDOR_ID" -Body $vUpdate | Out-Null
    }
}


# ============================================================
Write-Host "`n  BLOCK 3 - Dependency CRUD" -ForegroundColor White
Write-Host "  ────────────────────────────────────────────────"

if ($SC_ASSESS_ID) {
    # 3.1  Create dependency (with CVE)
    $dBody = @{
        assessment_id = $SC_ASSESS_ID
        name          = "log4j-core"
        version       = "2.14.1"
        package_type  = "maven"
        source        = "direct"
        cve_ids       = @("CVE-2021-44228", "CVE-2021-45046")
        cvss_score    = 10.0
    } | ConvertTo-Json -Compress

    $r = Invoke-API "POST .../dependencies (create w/ CVE)" `
        -Method POST -Url "$BASE/api/v1/supply-chain/$SC_ASSESS_ID/dependencies" -Body $dBody -ExpectedCode 201
    if ($r.code -eq "201") {
        $parsed = $r.body | ConvertFrom-Json
        $SC_DEP_ID = $parsed.id
        Write-Host "        dep id: $SC_DEP_ID  risk: $($parsed.risk_level) ($($parsed.risk_score))" -ForegroundColor Gray
    }

    # 3.2  Create dependency (no CVE)
    $dBody2 = @{
        assessment_id = $SC_ASSESS_ID
        name          = "express"
        version       = "4.18.2"
        package_type  = "npm"
        source        = "direct"
    } | ConvertTo-Json -Compress
    Invoke-API "POST .../dependencies (no CVE)" `
        -Method POST -Url "$BASE/api/v1/supply-chain/$SC_ASSESS_ID/dependencies" -Body $dBody2 -ExpectedCode 201 | Out-Null

    # 3.3  List dependencies
    $r = Invoke-API "GET .../dependencies (list)" `
        -Url "$BASE/api/v1/supply-chain/$SC_ASSESS_ID/dependencies"
    if ($r.code -eq "200") {
        $deps = $r.body | ConvertFrom-Json
        Write-Host "        total deps: $($deps.Count)" -ForegroundColor Gray
    }

    # 3.4  Filter by risk level
    Invoke-API "GET .../dependencies?risk_level=High (filter)" `
        -Url "$BASE/api/v1/supply-chain/$SC_ASSESS_ID/dependencies?risk_level=High" | Out-Null

    # 3.5  Get single dependency
    if ($SC_DEP_ID) {
        Invoke-API "GET .../dependencies/{id} (detail)" `
            -Url "$BASE/api/v1/supply-chain/$SC_ASSESS_ID/dependencies/$SC_DEP_ID" | Out-Null
    }

    # 3.6  Update dependency
    if ($SC_DEP_ID) {
        $dUpdate = @{ notes = "Known Log4Shell - critical"; cve_ids = @("CVE-2021-44228","CVE-2021-45046","CVE-2021-45105") } | ConvertTo-Json -Compress
        Invoke-API "PUT .../dependencies/{id} (update)" `
            -Method PUT -Url "$BASE/api/v1/supply-chain/$SC_ASSESS_ID/dependencies/$SC_DEP_ID" -Body $dUpdate | Out-Null
    }

    # 3.7  Bulk create
    $bulkBody = @(
        @{ assessment_id = $SC_ASSESS_ID; name = "lodash"; version = "4.17.21"; package_type = "npm" },
        @{ assessment_id = $SC_ASSESS_ID; name = "requests"; version = "2.28.0"; package_type = "pip"; cve_ids = @("CVE-2023-32681") }
    ) | ConvertTo-Json -Compress
    Invoke-API "POST .../dependencies/bulk (bulk create)" `
        -Method POST -Url "$BASE/api/v1/supply-chain/$SC_ASSESS_ID/dependencies/bulk" -Body $bulkBody -ExpectedCode 201 | Out-Null
}


# ============================================================
Write-Host "`n  BLOCK 4 - Risk Scoring [CCCS]" -ForegroundColor White
Write-Host "  ────────────────────────────────────────────────"

if ($SC_ASSESS_ID) {
    $r = Invoke-API "POST .../score (recalculate)" `
        -Method POST -Url "$BASE/api/v1/supply-chain/$SC_ASSESS_ID/score"
    if ($r.code -eq "200") {
        $score = $r.body | ConvertFrom-Json
        Write-Host "        overall_risk_score: $($score.overall_risk_score)  level: $($score.overall_risk_level)" -ForegroundColor Gray
        Write-Host "        tech sensitivity: $($score.technology_sensitivity)  avg vendor risk: $($score.avg_supplier_risk)%" -ForegroundColor Gray
        Write-Host "        deployment risk: $($score.deployment_risk)  critical deps: $($score.dependency_critical_count)" -ForegroundColor Gray
    }

    # Verify assessment was updated
    $r2 = Invoke-API "GET .../assess after scoring (verify)" `
        -Url "$BASE/api/v1/supply-chain/$SC_ASSESS_ID"
    if ($r2.code -eq "200") {
        $a = $r2.body | ConvertFrom-Json
        if ($a.overall_risk_score -gt 0) {
            Write-Host "  [PASS] Assessment risk score persisted: $($a.overall_risk_score) ($($a.overall_risk_level))" -ForegroundColor Green
            $script:pass += 1
        } else {
            Write-Host "  [FAIL] Assessment risk score not persisted" -ForegroundColor Red
            $script:fail += 1
            $script:errors += "Risk score not persisted after recalculate"
        }
    }
}


# ============================================================
Write-Host "`n  BLOCK 5 - SBOM Parsing" -ForegroundColor White
Write-Host "  ────────────────────────────────────────────────"

if ($SC_ASSESS_ID) {
    # 5.1  CycloneDX SBOM
    $cdxBody = @{
        sbom_content = @{
            bomFormat   = "CycloneDX"
            specVersion = "1.4"
            components  = @(
                @{ name = "chalk"; version = "5.0.0"; type = "library"; purl = "pkg:npm/chalk@5.0.0" },
                @{ name = "axios"; version = "1.4.0"; type = "library"; purl = "pkg:npm/axios@1.4.0" },
                @{
                    name = "node-forge"; version = "1.3.0"; type = "library"; purl = "pkg:npm/node-forge@1.3.0"
                    licenses = @(@{ license = @{ id = "MIT" } })
                }
            )
        }
        sbom_format = "cyclonedx"
    } | ConvertTo-Json -Depth 6 -Compress

    $r = Invoke-API "POST .../sbom/parse (CycloneDX)" `
        -Method POST -Url "$BASE/api/v1/supply-chain/$SC_ASSESS_ID/sbom/parse" -Body $cdxBody
    if ($r.code -eq "200") {
        $sbom = $r.body | ConvertFrom-Json
        Write-Host "        format: $($sbom.format_detected)  components: $($sbom.component_count)  warnings: $($sbom.warnings.Count)" -ForegroundColor Gray
    }

    # 5.2  SPDX SBOM
    $spdxBody = @{
        sbom_content = @{
            spdxVersion = "SPDX-2.3"
            packages    = @(
                @{ name = "django"; versionInfo = "4.2.0"; licenseConcluded = "BSD-3-Clause"; downloadLocation = "https://pypi.org/project/Django/" },
                @{ name = "flask"; versionInfo = "2.3.0"; licenseConcluded = "BSD-3-Clause" }
            )
        }
        sbom_format = "spdx"
    } | ConvertTo-Json -Depth 5 -Compress

    $r = Invoke-API "POST .../sbom/parse (SPDX)" `
        -Method POST -Url "$BASE/api/v1/supply-chain/$SC_ASSESS_ID/sbom/parse" -Body $spdxBody
    if ($r.code -eq "200") {
        $sbom = $r.body | ConvertFrom-Json
        Write-Host "        format: $($sbom.format_detected)  components: $($sbom.component_count)" -ForegroundColor Gray
    }
}


# ============================================================
Write-Host "`n  BLOCK 6 - ML Enrichment" -ForegroundColor White
Write-Host "  ────────────────────────────────────────────────"

if ($SC_ASSESS_ID) {
    $enrichBody = @{ dependency_ids = $null } | ConvertTo-Json -Compress
    $r = Invoke-API "POST .../dependencies/enrich [ML]" `
        -Method POST -Url "$BASE/api/v1/supply-chain/$SC_ASSESS_ID/dependencies/enrich" -Body $enrichBody
    if ($r.code -eq "200") {
        $er = $r.body | ConvertFrom-Json
        Write-Host "        enriched: $($er.enriched)  skipped: $($er.skipped)  errors: $($er.errors.Count)" -ForegroundColor Gray
    }
}


# ============================================================
Write-Host "`n  BLOCK 7 - Cleanup and Delete" -ForegroundColor White
Write-Host "  ────────────────────────────────────────────────"

if ($SC_DEP_ID -and $SC_ASSESS_ID) {
    Invoke-API "DELETE .../dependencies/{id}" `
        -Method DELETE -Url "$BASE/api/v1/supply-chain/$SC_ASSESS_ID/dependencies/$SC_DEP_ID" -ExpectedCode 204 | Out-Null
}

if ($SC_VENDOR_ID -and $SC_ASSESS_ID) {
    Invoke-API "DELETE .../vendors/{id}" `
        -Method DELETE -Url "$BASE/api/v1/supply-chain/$SC_ASSESS_ID/vendors/$SC_VENDOR_ID" -ExpectedCode 204 | Out-Null
}

if ($SC_ASSESS_ID) {
    Invoke-API "DELETE /supply-chain/{id}" `
        -Method DELETE -Url "$BASE/api/v1/supply-chain/$SC_ASSESS_ID" -ExpectedCode 204 | Out-Null

    # Verify deletion
    Invoke-API "GET /supply-chain/{id} after delete (404)" `
        -Url "$BASE/api/v1/supply-chain/$SC_ASSESS_ID" -ExpectedCode 404 | Out-Null
}


# ============================================================
# Summary
# ============================================================
Write-Host "`n========================================================"
Write-Host "  SUPPLY CHAIN E2E RESULTS" -ForegroundColor Cyan
Write-Host "========================================================" 
Write-Host "  Passed : $pass" -ForegroundColor Green
Write-Host "  Failed : $fail" -ForegroundColor $(if ($fail -gt 0) { "Red" } else { "Green" })
if ($errors.Count -gt 0) {
    Write-Host "`n  Failures:" -ForegroundColor Red
    $errors | ForEach-Object { Write-Host "    - $_" -ForegroundColor Yellow }
}
Write-Host ""

# Cleanup temp file
Remove-Item $TMP -ErrorAction SilentlyContinue

exit $fail
