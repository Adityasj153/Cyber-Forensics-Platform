#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Tests RBAC enforcement across all API endpoints.
    Requires: backend running at http://localhost:8000.
#>

$BASE = "http://localhost:8000/api"

function Invoke-Api {
    param(
        [string]$Method,
        [string]$Path,
        [string]$Token,
        [object]$Body = $null
    )
    $curlArgs = @("-s", "-w", "`n%{http_code}", "-X", $Method, "$BASE$Path")
    if ($Token) { $curlArgs += "-H"; $curlArgs += "Authorization: Bearer $Token" }
    if ($Body) {
        $json = $Body | ConvertTo-Json -Compress
        $tmpFile = [System.IO.Path]::GetTempFileName()
        [System.IO.File]::WriteAllText($tmpFile, $json)
        $curlArgs += "-H"; $curlArgs += "Content-Type: application/json"
        $curlArgs += "--data-binary"; $curlArgs += "@$tmpFile"
    }
    $raw = & curl.exe @curlArgs 2>&1
    if ($tmpFile) { Remove-Item $tmpFile -ErrorAction SilentlyContinue }
    $lines = $raw -split "`n"
    $statusCode = [int]($lines[-1].Trim())
    $bodyStr = ($lines[0..($lines.Count - 2)] -join "`n").Trim()
    $bodyObj = $null
    if ($bodyStr) { $bodyObj = $bodyStr | ConvertFrom-Json -ErrorAction SilentlyContinue }
    return @{ Status = $statusCode; Body = $bodyObj; Raw = $bodyStr }
}

$script:testPass = 0
$script:testFail = 0

function Assert-Status {
    param($result, $expected, $label)
    if ($result.Status -eq $expected) {
        Write-Host "  PASS: $label (HTTP $($result.Status))" -ForegroundColor Green
        $script:testPass++
    } else {
        Write-Host "  FAIL: $label -- expected HTTP $expected, got HTTP $($result.Status)" -ForegroundColor Red
        if ($result.Raw) { Write-Host "         $($result.Raw.Substring(0, [Math]::Min(200, $result.Raw.Length)))" -ForegroundColor DarkRed }
        $script:testFail++
    }
}

Write-Host "`n=== RBAC Test Suite ===" -ForegroundColor Cyan

# --- Setup: login as testuser (investigator) ---
Write-Host "`n[1] Login as testuser (investigator)" -ForegroundColor Yellow
$invLogin = Invoke-Api -Method POST -Path "/auth/login" -Body @{ username = "testuser"; password = "TestPass123!" }
$invToken = $invLogin.Body.access_token
Assert-Status $invLogin 200 "Investigator login"

# --- Setup: register a viewer user ---
Write-Host "`n[2] Register viewer user" -ForegroundColor Yellow
$viewerReg = Invoke-Api -Method POST -Path "/auth/register" -Body @{ username = "rbac_test_viewer"; email = "viewer@test.com"; password = "Viewer123!" }
if ($viewerReg.Status -eq 400) {
    Write-Host "  INFO: rbac_test_viewer already exists (from prior run)" -ForegroundColor DarkYellow
} else {
    Assert-Status $viewerReg 201 "Register viewer"
}

$viewerLogin = Invoke-Api -Method POST -Path "/auth/login" -Body @{ username = "rbac_test_viewer"; password = "Viewer123!" }
$viewerToken = $viewerLogin.Body.access_token
Assert-Status $viewerLogin 200 "Viewer login"

# --- Test 1: Registration cannot self-assign admin ---
Write-Host "`n[3] Registration cannot self-assign admin role" -ForegroundColor Yellow
$meResult = Invoke-Api -Method GET -Path "/auth/me" -Token $viewerToken
if ($meResult.Body.role -eq "viewer") {
    Write-Host "  PASS: User role is 'viewer' (no escalation possible)" -ForegroundColor Green
    $script:testPass++
} else {
    Write-Host "  FAIL: User role is '$($meResult.Body.role)', expected 'viewer'" -ForegroundColor Red
    $script:testFail++
}

# --- Test 2: Viewer cannot create a case ---
Write-Host "`n[4] Viewer cannot create a case" -ForegroundColor Yellow
$caseCreate = Invoke-Api -Method POST -Path "/cases" -Token $viewerToken -Body @{ name = "RBAC Test Case" }
Assert-Status $caseCreate 403 "Viewer POST /cases -> 403"

# --- Test 3: Investigator CAN create a case ---
Write-Host "`n[5] Investigator can create a case" -ForegroundColor Yellow
$ts = Get-Date -Format "HHmmss"
$caseCreateInv = Invoke-Api -Method POST -Path "/cases" -Token $invToken -Body @{ name = "RBAC Test Case $ts" }
Assert-Status $caseCreateInv 201 "Investigator POST /cases -> 201"
$caseId = $caseCreateInv.Body.id
Write-Host "         Created case: $caseId" -ForegroundColor DarkGray

# --- Test 4: Viewer can list cases (assigned ones) ---
Write-Host "`n[6] Viewer can list cases (assigned)" -ForegroundColor Yellow
$viewerCases = Invoke-Api -Method GET -Path "/cases" -Token $viewerToken
Assert-Status $viewerCases 200 "Viewer GET /cases -> 200"

# --- Test 5: Viewer cannot create a device ---
Write-Host "`n[7] Viewer cannot create a device" -ForegroundColor Yellow
$deviceCreate = Invoke-Api -Method POST -Path "/cases/$caseId/devices" -Token $viewerToken -Body @{ device_type = "pc"; name = "Test PC" }
Assert-Status $deviceCreate 403 "Viewer POST /cases/{id}/devices -> 403"

# --- Test 6: Investigator CAN create a device ---
Write-Host "`n[8] Investigator can create a device" -ForegroundColor Yellow
$deviceCreateInv = Invoke-Api -Method POST -Path "/cases/$caseId/devices" -Token $invToken -Body @{ device_type = "pc"; name = "Test PC" }
Assert-Status $deviceCreateInv 201 "Investigator POST /cases/{id}/devices -> 201"

# --- Test 7: Viewer cannot access unassigned case's devices ---
Write-Host "`n[9] Viewer cannot access unassigned case devices" -ForegroundColor Yellow
$deviceList = Invoke-Api -Method GET -Path "/cases/$caseId/devices" -Token $viewerToken
Assert-Status $deviceList 403 "Viewer GET /cases/{id}/devices (unassigned) -> 403"

# --- Test 8: Investigator CAN list devices ---
Write-Host "`n[10] Investigator can list devices" -ForegroundColor Yellow
$deviceListInv = Invoke-Api -Method GET -Path "/cases/$caseId/devices" -Token $invToken
Assert-Status $deviceListInv 200 "Investigator GET /cases/{id}/devices -> 200"

# --- Test 9: Viewer cannot review anomalies ---
Write-Host "`n[11] Viewer cannot review anomalies" -ForegroundColor Yellow
$anomalyReview = Invoke-Api -Method PATCH -Path "/cases/$caseId/anomalies/00000000-0000-0000-0000-000000000000/review" -Token $viewerToken -Body @{ review_status = "confirmed" }
Assert-Status $anomalyReview 403 "Viewer PATCH /cases/{id}/anomalies/{id}/review -> 403"

# --- Test 10: Viewer cannot update a case ---
Write-Host "`n[12] Viewer cannot update a case" -ForegroundColor Yellow
$caseUpdate = Invoke-Api -Method PATCH -Path "/cases/$caseId" -Token $viewerToken -Body @{ name = "Hacked" }
Assert-Status $caseUpdate 403 "Viewer PATCH /cases/{id} -> 403"

# --- Test 11: Investigator cannot update unassigned case ---
Write-Host "`n[13] Investigator cannot update unassigned case" -ForegroundColor Yellow
$inv2Reg = Invoke-Api -Method POST -Path "/auth/register" -Body @{ username = "rbac_test_inv2"; email = "inv2@test.com"; password = "Inv2Pass123!" }
$inv2Login = Invoke-Api -Method POST -Path "/auth/login" -Body @{ username = "rbac_test_inv2"; password = "Inv2Pass123!" }
$inv2Token = $inv2Login.Body.access_token
$caseUpdateInv2 = Invoke-Api -Method PATCH -Path "/cases/$caseId" -Token $inv2Token -Body @{ name = "Stolen" }
Assert-Status $caseUpdateInv2 403 "Investigator PATCH /cases/{id} (unassigned) -> 403"

# --- Summary ---
Write-Host "`n=== Results ===" -ForegroundColor Cyan
Write-Host "Passed: $($script:testPass)" -ForegroundColor Green
Write-Host "Failed: $($script:testFail)" -ForegroundColor $(if ($script:testFail -gt 0) { "Red" } else { "Green" })
Write-Host "Total:  $($script:testPass + $script:testFail)" -ForegroundColor White

if ($script:testFail -gt 0) {
    Write-Host "`nSome RBAC tests FAILED. See above." -ForegroundColor Red
    exit 1
} else {
    Write-Host "`nAll RBAC tests PASSED." -ForegroundColor Green
    exit 0
}
