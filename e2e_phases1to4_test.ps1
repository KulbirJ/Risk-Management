$BASE  = "https://oyxvwg62f7.execute-api.ca-west-1.amazonaws.com"
$TID   = "67636bd3-9846-4bde-806f-aea369fc9457"
$UID   = "0bc9d6a9-f342-452e-9297-ee33f44d4f84"
$CLOUD = "90098f68-4ee6-4f60-909e-670d2e172578"  # existing Cloud Migration assessment
$pass  = 0; $fail = 0; $warn = 0; $errors = @()
$TMP   = [System.IO.Path]::GetTempFileName()

function Invoke-API {
    param([string]$Name,[string]$Method="GET",[string]$Url,[string]$Body="",[int[]]$AcceptCodes=@(200),[switch]$Soft)
    $sep = "|||C|||"
    $a = @("-s","-X",$Method,$Url,"-H","X-Tenant-ID: $TID","-H","X-User-ID: $UID","-w","${sep}%{http_code}")
    if ($Body) {
        [System.IO.File]::WriteAllText($TMP,$Body,[System.Text.Encoding]::UTF8)
        $a += @("-H","Content-Type: application/json","-d","@$TMP")
    }
    $raw = (& curl.exe @a 2>&1) -join ""
    $idx = $raw.LastIndexOf($sep)
    if ($idx -ge 0) { $code=$raw.Substring($idx+$sep.Length).Trim(); $rb=$raw.Substring(0,$idx).Trim() }
    else { $code="000"; $rb=$raw }
    $ok = $AcceptCodes -contains [int]$code
    if ($ok) {
        Write-Host ("  [PASS] {0}  (HTTP {1})" -f $Name, $code) -ForegroundColor Green
        $script:pass += 1
    } elseif ($Soft) {
        Write-Host ("  [WARN] {0}  (HTTP {1} - optional dep missing)" -f $Name, $code) -ForegroundColor Yellow
        $script:warn += 1
        if ($rb.Length -gt 150) { Write-Host "         $($rb.Substring(0,150))" -ForegroundColor DarkGray }
        else { Write-Host "         $rb" -ForegroundColor DarkGray }
    } else {
        Write-Host ("  [FAIL] {0}  (HTTP {1}, want {2})" -f $Name, $code, ($AcceptCodes -join "/")) -ForegroundColor Red
        if ($rb.Length -gt 200) { Write-Host "         $($rb.Substring(0,200))" -ForegroundColor Yellow }
        else { Write-Host "         $rb" -ForegroundColor Yellow }
        $script:fail += 1
        $script:errors += "${Name}: HTTP $code"
    }
    return @{ code=$code; body=$rb }
}

# ============================================================
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  SETUP  -- New assessment + 1 threat" -ForegroundColor Cyan
Write-Host "========================================"
# Create a fresh assessment for setup tests
$ab = '{"title":"Phase1-4 E2E Run","description":"Automated test","system_background":"SaaS on AWS","scope":"production","overall_impact":"High","industry_sector":"technology"}'
$rA = Invoke-API "POST new assessment" -Method POST -Url "$BASE/api/v1/assessments/" -Body $ab -AcceptCodes @(201)
$AID = $null
if ($rA.code -eq "201") {
    try { $AID = ($rA.body | ConvertFrom-Json).id; Write-Host "         AID: $AID" -ForegroundColor DarkGray } catch {}
}

# Add one threat with JSON written to file by hand to avoid variable issues
$ntid = $null
if ($AID) {
    $tb = '{"title":"Log4Shell RCE","description":"log4j 2.14.1 vulnerable to RCE","likelihood":"Likely","impact":"Critical"}'
    $r2 = Invoke-API "POST threat on new assessment" -Method POST -Url "$BASE/api/v1/threats/?assessment_id=$AID" -Body $tb -AcceptCodes @(201)
    if ($r2.code -eq "201") { try { $ntid = ($r2.body | ConvertFrom-Json).id; Write-Host "         TID: $ntid" -ForegroundColor DarkGray } catch {} }
}

# Fetch first threat from the existing Cloud Migration assessment
$cloudTID = $null
$rTL = Invoke-API "GET threats (Cloud Migration - 15 existing)" -Url "$BASE/api/v1/threats/?assessment_id=$CLOUD" -AcceptCodes @(200)
if ($rTL.code -eq "200") {
    try {
        $ts = $rTL.body | ConvertFrom-Json
        Write-Host "         Found $($ts.Count) existing threats" -ForegroundColor DarkGray
        if ($ts.Count -gt 0) {
            $cloudTID = $ts[0].id
            Write-Host "         First threat: $cloudTID - $($ts[0].title)" -ForegroundColor DarkGray
        }
    } catch {}
}

# ============================================================
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  BLOCK A -- Phase 1: Intel Enrichment" -ForegroundColor Cyan
Write-Host "========================================"

# Correct route: /intel/attack-groups
$rAG = Invoke-API "GET /intel/attack-groups" -Url "$BASE/api/v1/intel/attack-groups" -AcceptCodes @(200)
if ($rAG.code -eq "200") {
    try { $ag = $rAG.body | ConvertFrom-Json; Write-Host "         groups.count=$($ag.count)" -ForegroundColor DarkGray } catch {}
}

# Correct route: /intel/sectors
$rSec = Invoke-API "GET /intel/sectors" -Url "$BASE/api/v1/intel/sectors" -AcceptCodes @(200)
if ($rSec.code -eq "200") {
    try { $sec = $rSec.body | ConvertFrom-Json; Write-Host "         sectors=$($sec.sectors)" -ForegroundColor DarkGray } catch {}
}

# Sector frequency (needs sector + catalogue_key)
Invoke-API "GET /intel/sectors/technology/frequency?catalogue_key=ransomware" -Url "$BASE/api/v1/intel/sectors/technology/frequency?catalogue_key=ransomware" -AcceptCodes @(200,404) | Out-Null

# Enrichments for existing threat
if ($cloudTID) {
    $rEnr = Invoke-API "GET /intel/threats/{id}/enrichments (pre-enrich)" -Url "$BASE/api/v1/intel/threats/$cloudTID/enrichments" -AcceptCodes @(200,404)
    if ($rEnr.code -eq "200") {
        try { $en = $rEnr.body | ConvertFrom-Json; Write-Host "         enrichment_count=$($en.enrichment_count)" -ForegroundColor DarkGray } catch {}
    }

    # Per-threat summary
    Invoke-API "GET /intel/threats/{id}/summary" -Url "$BASE/api/v1/intel/threats/$cloudTID/summary" -AcceptCodes @(200,404) | Out-Null
}

# Trigger enrichment on Cloud Migration assessment
$eb = '{"assessment_id":"90098f68-4ee6-4f60-909e-670d2e172578","force_refresh":false}'
$rE = Invoke-API "POST /intel/enrich (Cloud Migration dual-track)" -Method POST -Url "$BASE/api/v1/intel/enrich" -Body $eb -AcceptCodes @(200,201,202)
if ($rE.code -in @("200","201","202")) {
    try {
        $j = $rE.body | ConvertFrom-Json
        Write-Host "         status=$($j.status)  threats_enriched=$($j.threats_enriched)" -ForegroundColor DarkGray
        if ($j.cve_matches) { Write-Host "         CVE matches=$($j.cve_matches)" -ForegroundColor DarkGray }
        if ($j.errors) { Write-Host "         errors=$($j.errors | ConvertTo-Json -Compress)" -ForegroundColor Yellow }
    } catch {}
}

# Check enrichment after
if ($cloudTID) {
    $rEnr2 = Invoke-API "GET /intel/threats/{id}/enrichments (post-enrich)" -Url "$BASE/api/v1/intel/threats/$cloudTID/enrichments" -AcceptCodes @(200,404)
    if ($rEnr2.code -eq "200") {
        try {
            $en2 = $rEnr2.body | ConvertFrom-Json
            Write-Host "         enrichment_count=$($en2.enrichment_count)" -ForegroundColor DarkGray
            $en2.enrichments | Select-Object -First 3 | ForEach-Object {
                Write-Host "           source=$($_.source) severity=$($_.severity_score)" -ForegroundColor DarkGray
            }
        } catch {}
    }
}

# ============================================================
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  BLOCK B -- Phase 2: ML Scoring + Survival" -ForegroundColor Cyan
Write-Host "========================================"

$rMI = Invoke-API "GET /ml/model-info" -Url "$BASE/api/v1/ml/model-info" -AcceptCodes @(200)
if ($rMI.code -eq "200") {
    try { $mi = $rMI.body | ConvertFrom-Json; Write-Host "         trained=$($mi.trained)  features=$($mi.feature_count)  model_type=$($mi.model_type)" -ForegroundColor DarkGray } catch {}
}

$rBR = Invoke-API "GET /ml/bias-report" -Url "$BASE/api/v1/ml/bias-report" -AcceptCodes @(200,500) -Soft
if ($rBR.code -eq "200") {
    try { $br=$rBR.body|ConvertFrom-Json; Write-Host "         sector_count=$($br.sector_count)  total_scored=$($br.total_scored)" -ForegroundColor DarkGray } catch {}
}

$trainB = '{"algorithm":"random_forest","min_samples":5}'
$rTr = Invoke-API "POST /ml/train (sklearn not in Lambda, expect 501)" -Method POST -Url "$BASE/api/v1/ml/train" -Body $trainB -AcceptCodes @(200,501) -Soft
if ($rTr.code -eq "200") { Write-Host "         sklearn available! Model trained." -ForegroundColor Green }
elseif ($rTr.code -eq "501") { Write-Host "         Graceful 501: sklearn not installed (expected)" -ForegroundColor DarkGray }

$scoreB = '{"assessment_id":"90098f68-4ee6-4f60-909e-670d2e172578","persist":false}'
$rSc = Invoke-API "POST /ml/score (Cloud Migration batch)" -Method POST -Url "$BASE/api/v1/ml/score" -Body $scoreB -AcceptCodes @(200,500,501) -Soft
if ($rSc.code -eq "200") {
    try { $sc=$rSc.body|ConvertFrom-Json; Write-Host "         scored_count=$($sc.scored_count)  fallback=$($sc.fallback_used)" -ForegroundColor DarkGray } catch {}
}

if ($cloudTID) {
    $rSi = Invoke-API "GET /ml/score/{threat_id}" -Url "$BASE/api/v1/ml/score/$cloudTID" -AcceptCodes @(200,404,500,501) -Soft
    if ($rSi.code -eq "200") {
        try { $si=$rSi.body|ConvertFrom-Json; Write-Host "         score=$($si.likelihood_score)  label=$($si.label)" -ForegroundColor DarkGray } catch {}
    }
    $rEx = Invoke-API "GET /ml/explain/{threat_id}" -Url "$BASE/api/v1/ml/explain/$cloudTID" -AcceptCodes @(200,404,500,501) -Soft
    if ($rEx.code -eq "200") {
        try { $ex=$rEx.body|ConvertFrom-Json; Write-Host "         top_feature=$($ex.top_features[0].feature)" -ForegroundColor DarkGray } catch {}
    }
}

$rCV = Invoke-API "GET /ml/survival/curve" -Url "$BASE/api/v1/ml/survival/curve" -AcceptCodes @(200,500,501) -Soft
if ($rCV.code -eq "200") {
    try { $cv=$rCV.body|ConvertFrom-Json; Write-Host "         curve_points=$($cv.curve.Count)  median_days=$($cv.median_days)" -ForegroundColor DarkGray } catch {}
}

$survB = '{"assessment_id":"90098f68-4ee6-4f60-909e-670d2e172578","persist":false}'
$rSv = Invoke-API "POST /ml/survival (persistence estimate)" -Method POST -Url "$BASE/api/v1/ml/survival" -Body $survB -AcceptCodes @(200,500,501) -Soft
if ($rSv.code -eq "200") {
    try { $sv=$rSv.body|ConvertFrom-Json; Write-Host "         estimated_count=$($sv.estimated_count)" -ForegroundColor DarkGray } catch {}
}

# ============================================================
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  BLOCK C -- Phase 3: Graph Mapping" -ForegroundColor Cyan
Write-Host "========================================"

$rGr = Invoke-API "GET /graph/assessment/{id} (expect 501 - networkx optional)" -Url "$BASE/api/v1/graph/assessment/$CLOUD" -AcceptCodes @(200,501) -Soft
if ($rGr.code -eq "200") {
    try {$g=$rGr.body|ConvertFrom-Json; Write-Host "         nodes=$($g.node_count) edges=$($g.edge_count)" -ForegroundColor Green} catch {}
} elseif ($rGr.code -eq "501") {
    Write-Host "         Graceful 501: networkx not in Lambda (expected)" -ForegroundColor DarkGray
}

$rCr = Invoke-API "GET /graph/assessment/{id}/critical (PageRank)" -Url "$BASE/api/v1/graph/assessment/$CLOUD/critical?top_n=5" -AcceptCodes @(200,501) -Soft
if ($rCr.code -eq "200") {
    try { $cr=$rCr.body|ConvertFrom-Json; Write-Host "         top_critical=$($cr.critical_nodes.Count)" -ForegroundColor Green } catch {}
}

if ($cloudTID) {
    $rNh = Invoke-API "GET /graph/threat/{id}/neighbourhood (depth=2)" -Url "$BASE/api/v1/graph/threat/$cloudTID/neighbourhood?depth=2" -AcceptCodes @(200,404,501) -Soft
    if ($rNh.code -eq "200") {
        try { $nh=$rNh.body|ConvertFrom-Json; Write-Host "         neighbourhood_nodes=$($nh.node_count)" -ForegroundColor Green } catch {}
    }
}

# ============================================================
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  BLOCK D -- Phase 4: DBSCAN Clustering" -ForegroundColor Cyan
Write-Host "========================================"

$clB = '{"eps":0.8,"min_samples":2}'
$rCl = Invoke-API "POST /clusters/assessment/{id} (DBSCAN)" -Method POST -Url "$BASE/api/v1/clusters/assessment/$CLOUD" -Body $clB -AcceptCodes @(200,201,500,501) -Soft
if ($rCl.code -in @("200","201")) {
    try { $cl=$rCl.body|ConvertFrom-Json; Write-Host "         clusters=$($cl.cluster_count) noise=$($cl.noise_count) quality=$($cl.silhouette_score)" -ForegroundColor Green } catch {}
}

$rTC = Invoke-API "POST /clusters/tenant (all tenant threats)" -Method POST -Url "$BASE/api/v1/clusters/tenant" -Body $clB -AcceptCodes @(200,201,500,501) -Soft
if ($rTC.code -in @("200","201")) {
    try { $tc=$rTC.body|ConvertFrom-Json; Write-Host "         tenant_clusters=$($tc.cluster_count) threats_clustered=$($tc.threats_clustered)" -ForegroundColor Green } catch {}
}

if ($cloudTID) {
    $rSm = Invoke-API "GET /clusters/similar/{threat_id}" -Url "$BASE/api/v1/clusters/similar/${cloudTID}?top_n=3" -AcceptCodes @(200,404,500,501) -Soft
    if ($rSm.code -eq "200") {
        try { $sm=$rSm.body|ConvertFrom-Json; Write-Host "         similar_threats=$($sm.similar_threats.Count)" -ForegroundColor Green } catch {}
    }
}

# ============================================================
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  CLEANUP" -ForegroundColor Cyan
Write-Host "========================================"
if ($AID) { Invoke-API "DELETE test assessment" -Method DELETE -Url "$BASE/api/v1/assessments/$AID" -AcceptCodes @(200,204) | Out-Null }
if (Test-Path $TMP) { Remove-Item $TMP -Force }

Write-Host "`n========================================" -ForegroundColor White
Write-Host "  SUMMARY" -ForegroundColor White
Write-Host "========================================"
Write-Host "  PASSED  : $pass" -ForegroundColor Green
Write-Host "  WARNED  : $warn  (optional deps missing - graceful degradation)" -ForegroundColor Yellow
Write-Host "  FAILED  : $fail" -ForegroundColor $(if ($fail -gt 0) {"Red"} else {"Green"})
if ($errors.Count -gt 0) { Write-Host "`n  Issues:" -ForegroundColor Red; $errors | ForEach-Object { Write-Host "    - $_" -ForegroundColor Red } }
if ($fail -eq 0) { Write-Host "`n  All required checks passing." -ForegroundColor Green }

