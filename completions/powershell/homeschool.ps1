# Homeschool PowerShell Completions

Register-ArgumentCompleter -CommandName 'homeschool' -ParameterName 'shell' -ScriptBlock {
    param($wordToComplete, $commandAst, $cursorPosition)
    @('bash', 'zsh', 'powershell') | Where-Object { $_ -like "$wordToComplete*" }
}

Register-ArgumentCompleter -CommandName 'homeschool' -ParameterName 'database' -ScriptBlock {
    param($wordToComplete, $commandAst, $cursorPosition)
    @('default', 'essay', 'homework') | Where-Object { $_ -like "$wordToComplete*" }
}

Register-ArgumentCompleter -CommandName 'homeschool' -ParameterName 'log-level' -ScriptBlock {
    param($wordToComplete, $commandAst, $cursorPosition)
    @('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL') | Where-Object { $_ -like "$wordToComplete*" }
}