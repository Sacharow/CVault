param(
    [string]$ExecutablePath = (Join-Path $PSScriptRoot "dist\CVault.exe")
)

$ErrorActionPreference = "Stop"

$resolvedPath = (Resolve-Path -LiteralPath $ExecutablePath).Path
$certificateSubject = "CN=CVault Local Development"
$certificate = Get-ChildItem Cert:\CurrentUser\My |
    Where-Object {
        $_.Subject -eq $certificateSubject -and
        $_.HasPrivateKey -and
        $_.NotAfter -gt (Get-Date)
    } |
    Sort-Object NotAfter -Descending |
    Select-Object -First 1

if (-not $certificate) {
    $certificate = New-SelfSignedCertificate `
        -Type CodeSigningCert `
        -Subject $certificateSubject `
        -CertStoreLocation Cert:\CurrentUser\My `
        -HashAlgorithm SHA256 `
        -KeyAlgorithm RSA `
        -KeyLength 3072 `
        -NotAfter (Get-Date).AddYears(2)
}

$signature = Set-AuthenticodeSignature `
    -FilePath $resolvedPath `
    -Certificate $certificate `
    -HashAlgorithm SHA256

$verifiedSignature = Get-AuthenticodeSignature -FilePath $resolvedPath
if (
    -not $verifiedSignature.SignerCertificate -or
    $verifiedSignature.SignerCertificate.Thumbprint -ne $certificate.Thumbprint
) {
    throw "The executable was not signed with the CVault development certificate."
}

Write-Host "Signed $resolvedPath"
Write-Host "Certificate: $($certificate.Subject) [$($certificate.Thumbprint)]"
Write-Host "Signature status: $($verifiedSignature.Status) - $($verifiedSignature.StatusMessage)"
Write-Warning "This self-signed certificate is not trusted by other PCs and may not bypass Smart App Control."
