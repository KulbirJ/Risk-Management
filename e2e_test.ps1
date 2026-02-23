# ============================================================
# End-to-End API Test Suite  (Windows / PowerShell / curl.exe)
# ============================================================
$BASE  = "https://oyxvwg62f7.execute-api.ca-west-1.amazonaws.com"
$TID   = "67636bd3-9846-4bde-806f-aea369fc9457"
$UID   = "0bc9d6a9-f342-452e-9297-ee33f44d4f84"

$pass = 0; $fail = 0; $errors = @()

# Temp file for sending JSON bodies (avoids curl.exe quoting issues on Windows)
$TMP = [System.IO.Path]::GetTempFileName()

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
        $e = "${Name}: got $code expected $ExpectedCode"
        $script:errors += $e
    } else {
        $script:pass += 1
    }
    return @{ code = $code; body = $respBody }
}

# ============================================================
Write-Host "`n======================================" -ForegroundColor White
Write-Host "  BLOCK 1 -- Health & Core Reads" -ForegroundColor White
Write-Host "======================================"

Invoke-API "GET /health" -Url "$BASE/health" | Out-Null
Invoke-API "GET /api/v1/assessments/" -Url "$BASE/api/v1/assessments/" | Out-Null
Invoke-API "GET /api/v1/active-risks/" -Url "$BASE/api/v1/active-risks/" | Out-Null
Invoke-API "GET /api/v1/audit-logs/" -Url "$BASE/api/v1/audit-logs/" | Out-Null

# ============================================================
Write-Host "`n======================================" -ForegroundColor White
Write-Host "  BLOCK 2 -- Assessment CRUD" -ForegroundColor White
Write-Host "======================================"

$assessBody = '{"title":"E2E-Test-Run","description":"Automated e2e","system_background":"E2E test system","scope":"Full scope","overall_impact":"High"}'
$r = Invoke-API "POST create assessment" -Method POST -Url "$BASE/api/v1/assessments/" -Body $assessBody -ExpectedCode 201
$newAssessId = $null
if ($r.code -eq "201") {
    try { $newAssessId = ($r.body | ConvertFrom-Json).id; Write-Host "        Created: $newAssessId" -ForegroundColor DarkGray } catch {}
}

if ($newAssessId) {
    Invoke-API "GET assessment by ID" -Url "$BASE/api/v1/assessments/$newAssessId" | Out-Null
    $upd = '{"title":"E2E-Test-Run-Updated","overall_impact":"Critical"}'
    Invoke-API "PATCH update assessment" -Method PATCH -Url "$BASE/api/v1/assessments/$newAssessId" -Body $upd | Out-Null
}

# ============================================================
Write-Host "`n======================================" -ForegroundColor White
Write-Host "  BLOCK 3 -- Threats" -ForegroundColor White
Write-Host "======================================"

$CLOUD = "90098f68-4ee6-4f60-909e-670d2e172578"
$r2 = Invoke-API "GET threats (Cloud Migration)" -Url "$BASE/api/v1/threats/?assessment_id=$CLOUD"
$existingThreatId = $null
if ($r2.code -eq "200") {
    try {
        $ts = $r2.body | ConvertFrom-Json
        Write-Host "        Found $($ts.Count) threats" -ForegroundColor DarkGray
        if ($ts.Count -gt 0) { $existingThreatId = $ts[0].id; Write-Host "        First: $($ts[0].id) -- $($ts[0].title)" -ForegroundColor DarkGray }
    } catch {}
}

$newThreatId = $null
if ($newAssessId) {
    $tBody = '{"title":"E2E SQL Injection Threat","description":"SQL injection via user input","likelihood":"Likely","impact":"High","category":"Application"}'
    $r3 = Invoke-API "POST create threat" -Method POST -Url "$BASE/api/v1/threats/?assessment_id=$newAssessId" -Body $tBody -ExpectedCode 201
    if ($r3.code -eq "201") {
        try { $newThreatId = ($r3.body | ConvertFrom-Json).id; Write-Host "        Created threat: $newThreatId" -ForegroundColor DarkGray } catch {}
    }
    if ($newThreatId) {
        Invoke-API "GET threat by ID" -Url "$BASE/api/v1/threats/$newThreatId" | Out-Null
    }
}

# ============================================================
Write-Host "`n======================================" -ForegroundColor White
Write-Host "  BLOCK 4 -- ATT&CK Framework" -ForegroundColor White
Write-Host "======================================"

$r4 = Invoke-API "GET /attack/tactics" -Url "$BASE/api/v1/attack/tactics"
if ($r4.code -eq "200") {
    try {
        $tacs = $r4.body | ConvertFrom-Json
        $withOrder = ($tacs | Where-Object { $null -ne $_.phase_order }).Count
        Write-Host "        Tactics: $($tacs.Count), with phase_order: $withOrder" -ForegroundColor DarkGray
        if ($withOrder -lt 14) {
            $script:errors += "Only $withOrder/14 tactics have phase_order populated"
            $script:fail += 1
        } else {
            $script:pass += 1
            $tacs | Sort-Object phase_order | Select-Object -First 3 | ForEach-Object {
                Write-Host "          $($_.phase_order). $($_.name)" -ForegroundColor DarkGray
            }
        }
    } catch {}
}

Invoke-API "GET /attack/sync-status" -Url "$BASE/api/v1/attack/sync-status" | Out-Null

$r4b = Invoke-API "GET techniques search (phishing)" -Url "$BASE/api/v1/attack/techniques/search?q=phishing"
if ($r4b.code -eq "200") {
    try {
        $ts = $r4b.body | ConvertFrom-Json
        $sample = $ts | Select-Object -First 1
        if ($sample) {
            $hasDetect = if ($sample.detection_text) { "present" } else { "NULL" }
            Write-Host "        Sample technique: $($sample.mitre_id) $($sample.name)  detection_text=$hasDetect" -ForegroundColor DarkGray
        }
    } catch {}
}

# ============================================================
Write-Host "`n======================================" -ForegroundColor White
Write-Host "  BLOCK 5 -- ATT&CK Mappings" -ForegroundColor White
Write-Host "======================================"

$TEST_THREAT = "3781360c-7769-4504-b394-ead23b1f2f71"
$r5 = Invoke-API "GET mappings for S3 threat" -Url "$BASE/api/v1/attack/threats/$TEST_THREAT/mappings"
if ($r5.code -eq "200") {
    try {
        $maps = $r5.body | ConvertFrom-Json
        Write-Host "        Mappings: $($maps.Count)" -ForegroundColor DarkGray
        $maps | ForEach-Object { Write-Host "          $($_.technique.mitre_id)  $($_.technique.name)  confidence=$($_.confidence_score)" -ForegroundColor DarkGray }
    } catch {}
}

# ============================================================
Write-Host "`n======================================" -ForegroundColor White
Write-Host "  BLOCK 6 -- Kill Chain" -ForegroundColor White
Write-Host "======================================"

$r6 = Invoke-API "GET existing kill chains" -Url "$BASE/api/v1/attack/threats/$TEST_THREAT/kill-chains"
if ($r6.code -eq "200") {
    try {
        $kcs = $r6.body | ConvertFrom-Json
        Write-Host "        Kill chains in DB: $($kcs.Count)" -ForegroundColor DarkGray
        if ($kcs.Count -gt 0) {
            $latest = $kcs | Sort-Object created_at -Descending | Select-Object -First 1
            Write-Host "        Latest: $($latest.id)  status=$($latest.status)  stages=$($latest.stages.Count)" -ForegroundColor DarkGray
            $nullTech = $latest.stages | Where-Object { -not $_.technique_id }
            if ($nullTech.Count -gt 0) {
                Write-Host "        FAIL: $($nullTech.Count) stage(s) missing technique_id" -ForegroundColor Red
                $script:fail += 1; $script:errors += "Existing KC has stages with null technique_id"
            } else {
                Write-Host "        OK: all $($latest.stages.Count) stages have technique_id set" -ForegroundColor Green
                $script:pass += 1
            }
            $latest.stages | Sort-Object stage_number | ForEach-Object {
                Write-Host "          Stage $($_.stage_number): $($_.mitre_id)  '$($_.technique_name)'  tech_id=$($_.technique_id)" -ForegroundColor DarkGray
            }
        }
    } catch {}
}

Write-Host "  [INFO] Generating fresh kill chain (Bedrock call ~15s)..." -ForegroundColor DarkGray
$r7 = Invoke-API "POST generate kill chain" -Method POST -Url "$BASE/api/v1/attack/threats/$TEST_THREAT/kill-chains" -Body "{}" -ExpectedCode 201
if ($r7.code -eq "201") {
    try {
        $kc = $r7.body | ConvertFrom-Json
        Write-Host "        scenario_name : $($kc.scenario_name)" -ForegroundColor DarkGray
        Write-Host "        stages        : $($kc.stages.Count)  status=$($kc.status)" -ForegroundColor DarkGray
        $nullNew = $kc.stages | Where-Object { -not $_.technique_id }
        if ($nullNew.Count -gt 0) {
            Write-Host "        FAIL: new KC has $($nullNew.Count) null technique_id stage(s)" -ForegroundColor Red
            $script:fail += 1; $script:errors += "New KC has null technique_ids"
        } else {
            Write-Host "        OK: all new stages have technique_id" -ForegroundColor Green
            $script:pass += 1
        }
        $kc.stages | Sort-Object stage_number | ForEach-Object {
            Write-Host "          Stage $($_.stage_number): $($_.mitre_id)  '$($_.technique_name)'  tech_id=$($_.technique_id)" -ForegroundColor DarkGray
        }
    } catch {}
}

# ============================================================
Write-Host "`n======================================" -ForegroundColor White
Write-Host "  BLOCK 7 -- Recommendations" -ForegroundColor White
Write-Host "======================================"

Invoke-API "GET all recommendations" -Url "$BASE/api/v1/recommendations/" | Out-Null
if ($existingThreatId) {
    Invoke-API "GET recommendations by threat" -Url "$BASE/api/v1/recommendations/?threat_id=$existingThreatId" | Out-Null
}

# ============================================================
Write-Host "`n======================================" -ForegroundColor White
Write-Host "  BLOCK 8 -- Cleanup" -ForegroundColor White
Write-Host "======================================"

if ($newAssessId) {
    Invoke-API "DELETE E2E assessment" -Method DELETE -Url "$BASE/api/v1/assessments/$newAssessId" -ExpectedCode 204 | Out-Null
}
if (Test-Path $TMP) { Remove-Item $TMP -Force }

# ============================================================
Write-Host "`n======================================" -ForegroundColor White
Write-Host "  SUMMARY" -ForegroundColor White
Write-Host "======================================"
Write-Host "  PASSED: $pass" -ForegroundColor Green
Write-Host ("  FAILED: {0}" -f $fail) -ForegroundColor $(if ($fail -gt 0) { "Red" } else { "Green" })
if ($errors.Count -gt 0) {
    Write-Host "`n  Failures:" -ForegroundColor Red
    $errors | ForEach-Object { Write-Host "    - $_" -ForegroundColor Red }
}
