function test_output_file_flag() {
    $TEMP_OUT_FILE = New-TemporaryFile
    
    Write-Host "   [EXEC] $env:AI_CMD -m `"Reply with the exact word BANANA`" -o `"$($TEMP_OUT_FILE.FullName)`""
    
    Invoke-Expression "$env:AI_CMD -m `"Reply with the exact word BANANA`" -o `"$($TEMP_OUT_FILE.FullName)`""
    
    $content = Get-Content $TEMP_OUT_FILE.FullName -Raw -ErrorAction SilentlyContinue
    if ($content -match "BANANA") {
        Write-Host "      -> Output file successfully created and verified" -ForegroundColor Green
    } else {
        Write-Host "      -> ❌ FAILED: Output file not created or verification failed" -ForegroundColor Red
        Write-Host "      -> Content of output file ($($TEMP_OUT_FILE.FullName)):"
        if ($content) { Write-Host $content } else { Write-Host "(file not found)" }
        cleanup_files @($TEMP_OUT_FILE.FullName)
        throw "Failed"
    }
    cleanup_files @($TEMP_OUT_FILE.FullName)
}

function run_category_3() {
    Write-Host "`n### Category 3: File System Modifiers ###" -ForegroundColor Green
    run_test "Output File Flag (-o)" "Ensures the output flag writes the model's response to the specified file." "test_output_file_flag"
}
