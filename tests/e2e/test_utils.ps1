# test_utils.ps1

$script:TESTS_TOTAL = 0
$script:TESTS_PASSED = 0
$script:TESTS_FAILED = 0

$env:VERBOSE = if ($env:VERBOSE) { $env:VERBOSE } else { "0" }

function log_verbose($msg) {
    if ($env:VERBOSE -eq "1") {
        Write-Host "   [DEBUG] $msg" -ForegroundColor Yellow
    }
}

function cleanup_files([string[]]$files) {
    if ($env:VERBOSE -eq "0") {
        foreach ($file in $files) {
            if (Test-Path $file) {
                Remove-Item -Force $file
            }
        }
    } else {
        log_verbose "Keeping temp file(s) for debugging: $($files -join ', ')"
    }
}

function run_test($test_name, $description, $func_name) {
    Write-Host "`n======================================================================" -ForegroundColor Yellow
    Write-Host "▶ TEST: $test_name" -ForegroundColor Yellow
    Write-Host "  $description"
    Write-Host "----------------------------------------------------------------------" -ForegroundColor Yellow

    $script:TESTS_TOTAL++
    
    $passed = $true
    if ($env:VERBOSE -eq "1") {
        try {
            & $func_name
        } catch {
            $passed = $false
            Write-Host $_.Exception.Message -ForegroundColor Red
        }
    } else {
        $temp_out = New-TemporaryFile
        try {
            & $func_name *>&1 | Out-File -FilePath $temp_out.FullName -Encoding UTF8
        } catch {
            $passed = $false
        }
        
        if (-not $passed) {
            Get-Content $temp_out.FullName | Write-Host
        } else {
            Select-String -Path $temp_out.FullName -Pattern '(\[EXEC\]|->)' | ForEach-Object { Write-Host $_.Line }
        }
        Remove-Item -Force $temp_out.FullName
    }

    if ($passed) {
        Write-Host "   -> ✅ TEST PASSED: $test_name" -ForegroundColor Green
        $script:TESTS_PASSED++
    } else {
        Write-Host "   -> ❌ TEST FAILED: $test_name" -ForegroundColor Red
        $script:TESTS_FAILED++
    }
}

function run_and_verify($expected, $out_file, $cmd) {
    Write-Host "   [EXEC] $cmd" -ForegroundColor Yellow
    
    $exit_code = 0
    try {
        Invoke-Expression $cmd
        $exit_code = $LASTEXITCODE
    } catch {
        $exit_code = 1
    }
    
    if ($exit_code -ne 0 -and $exit_code -ne $null) {
         Write-Host "      -> ❌ FAILED: Command failed with exit code $exit_code" -ForegroundColor Red
         throw "Command failed"
    }
    
    if ($expected -ne "NO_CHECK") {
        $content = Get-Content $out_file -Raw -ErrorAction SilentlyContinue
        if ($content -match [regex]::Escape($expected)) {
            Write-Host "      -> Verified: '$expected' found in output." -ForegroundColor Green
        } else {
            Write-Host "      -> ❌ FAILED: '$expected' not found in $out_file" -ForegroundColor Red
            if ($content) { Write-Host $content } else { Write-Host "(file not found)" }
            throw "Verification failed"
        }
    } else {
        Write-Host "      -> Verified: Command completed successfully." -ForegroundColor Green
    }
}

function print_summary() {
    Write-Host "`n======================================================================"
    Write-Host "🏆 INTEGRATION TEST SUMMARY"
    Write-Host "======================================================================"
    Write-Host "Total Tests Run : $script:TESTS_TOTAL"
    Write-Host "Tests Passed    : $script:TESTS_PASSED" -ForegroundColor Green
    if ($script:TESTS_FAILED -gt 0) {
        Write-Host "Tests Failed    : $script:TESTS_FAILED" -ForegroundColor Red
        exit 1
    } else {
        Write-Host "Tests Failed    : 0"
    }
    Write-Host "======================================================================"
}
