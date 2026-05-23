function test_help_flag() {
    $TEMP_OUT = New-TemporaryFile
    Write-Host "   [EXEC] $env:AI_CMD -h > `"$($TEMP_OUT.FullName)`""
    
    Invoke-Expression "$env:AI_CMD -h > `"$($TEMP_OUT.FullName)`" 2>&1"
    
    $content = Get-Content $TEMP_OUT.FullName -Raw -ErrorAction SilentlyContinue
    if ($content -match "JUST A REASONING VIRTUAL INTELLIGENT SENTINEL AGENTIC INTERFACE" -and $content -match "\[ SYSTEM READY \]") {
        Write-Host "      -> Help output successfully verified" -ForegroundColor Green
    } else {
        Write-Host "      -> ❌ FAILED: Help output verification failed" -ForegroundColor Red
        Write-Host "      -> Content of output file ($($TEMP_OUT.FullName)):"
        if ($content) { Write-Host $content } else { Write-Host "(file not found)" }
        cleanup_files @($TEMP_OUT.FullName)
        throw "Failed"
    }
    cleanup_files @($TEMP_OUT.FullName)
}

function test_version_flag() {
    $TEMP_OUT = New-TemporaryFile
    Write-Host "   [EXEC] $env:AI_CMD -v > `"$($TEMP_OUT.FullName)`""
    
    Invoke-Expression "$env:AI_CMD -v > `"$($TEMP_OUT.FullName)`" 2>&1"
    
    $content = Get-Content $TEMP_OUT.FullName -Raw -ErrorAction SilentlyContinue
    if ($content -match "Version") {
        Write-Host "      -> Version output successfully verified" -ForegroundColor Green
    } else {
        Write-Host "      -> ❌ FAILED: Version output verification failed" -ForegroundColor Red
        Write-Host "      -> Content of output file ($($TEMP_OUT.FullName)):"
        if ($content) { Write-Host $content } else { Write-Host "(file not found)" }
        cleanup_files @($TEMP_OUT.FullName)
        throw "Failed"
    }
    cleanup_files @($TEMP_OUT.FullName)
}

function test_list_models() {
    $TEMP_OUT = New-TemporaryFile
    Write-Host "   [EXEC] $env:AI_CMD -l > `"$($TEMP_OUT.FullName)`""
    
    Invoke-Expression "$env:AI_CMD -l > `"$($TEMP_OUT.FullName)`" 2>&1"
    $exit_code = $LASTEXITCODE
    
    if ($exit_code -eq 0) {
        Write-Host "      -> List models successfully executed" -ForegroundColor Green
    } else {
        Write-Host "      -> ❌ FAILED: List models execution failed with exit code $exit_code" -ForegroundColor Red
        Write-Host "      -> Content of output file ($($TEMP_OUT.FullName)):"
        $content = Get-Content $TEMP_OUT.FullName -Raw -ErrorAction SilentlyContinue
        if ($content) { Write-Host $content } else { Write-Host "(file not found)" }
        cleanup_files @($TEMP_OUT.FullName)
        throw "Failed"
    }
    cleanup_files @($TEMP_OUT.FullName)
}

function test_show_logo() {
    $TEMP_OUT = New-TemporaryFile
    Write-Host "   [EXEC] $env:AI_CMD --show-logo -v > `"$($TEMP_OUT.FullName)`""
    
    Invoke-Expression "$env:AI_CMD --show-logo -v > `"$($TEMP_OUT.FullName)`" 2>&1"
    
    $content = Get-Content $TEMP_OUT.FullName -Raw -ErrorAction SilentlyContinue
    if ($content -match "JARVIS") {
        Write-Host "      -> Show Logo successfully verified" -ForegroundColor Green
    } else {
        Write-Host "      -> ❌ FAILED: Show Logo verification failed" -ForegroundColor Red
        Write-Host "      -> Content of output file ($($TEMP_OUT.FullName)):"
        if ($content) { Write-Host $content } else { Write-Host "(file not found)" }
        cleanup_files @($TEMP_OUT.FullName)
        throw "Failed"
    }
    cleanup_files @($TEMP_OUT.FullName)
}

function run_category_1() {
    Write-Host "`n### Category 1: Informational & Immediate Exit ###" -ForegroundColor Green
    run_test "Help Flag (-h)" "Verifies that the help flag outputs the correct system diagnostic message." "test_help_flag"
    run_test "Version Flag (-v)" "Checks if the version flag correctly displays the JARVIS version information." "test_version_flag"
    run_test "List Models (-l)" "Ensures the list flag executes without errors to show available neural models." "test_list_models"
    run_test "Show Logo (--show-logo)" "Tests if the show logo flag successfully prints the JARVIS ASCII art." "test_show_logo"
}
