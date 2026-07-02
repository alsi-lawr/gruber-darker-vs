<#
.SYNOPSIS
    Rewrites README.md's relative image links to absolute raw.githubusercontent.com URLs
    and writes the result to overview.md, for use as the VSIX publish manifest's "overview".

    The Marketplace renders "overview" as a standalone file with no knowledge of this repo,
    so relative image paths (docs/images/*.png, the root-level logo) resolve to nothing there
    even though they work fine on GitHub. Other relative links (LICENSE, CONTRIBUTING.md, the
    releases page) are left untouched: they may not resolve on the Marketplace page either, but
    that's a broken link, not a broken screenshot.
#>
param(
    [Parameter(Mandatory)] [string]$Repo,
    [Parameter(Mandatory)] [string]$Ref,
    [string]$SourcePath = "README.md",
    [string]$OutputPath = "overview.md"
)

$ErrorActionPreference = "Stop"

$rawBase = "https://raw.githubusercontent.com/$Repo/$Ref/"
$content = Get-Content -Raw -Path $SourcePath

$isRelative = { param($path) $path -notmatch '^(https?:)?//' }

$content = [regex]::Replace(
    $content,
    '(?<attr>\bsrc)="(?<path>[^"]+)"',
    {
        param($m)
        $path = $m.Groups['path'].Value
        if (& $isRelative $path) {
            $m.Groups['attr'].Value + '="' + $rawBase + $path + '"'
        } else {
            $m.Value
        }
    }
)

$content = [regex]::Replace(
    $content,
    '(?<pre>!\[[^\]]*\]\()(?<path>[^)\s]+)(?<post>\))',
    {
        param($m)
        $path = $m.Groups['path'].Value
        if (& $isRelative $path) {
            $m.Groups['pre'].Value + $rawBase + $path + $m.Groups['post'].Value
        } else {
            $m.Value
        }
    }
)

Set-Content -Path $OutputPath -Value $content -NoNewline
Write-Host "Wrote $OutputPath from $SourcePath (images rewritten against $rawBase)"
