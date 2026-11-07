# Kane's Wrath - Distribution and Build Inventory

Date: 2026-11-07
Issue: #2
Research scope: executable identity and documented build variants.

## Reproducible local evidence

Observed installation location:
D:/Games/steam/steamapps/common/Command and Conquer 3 - Kane's Wrath/

Verified binary:
RetailExe/1.2/cnc3ep1.dat

SHA256:
14CE459E52366A176CC4B9F1E659089D19DA22404060481B61A1CB35C00286AD

PowerShell verification:
Get-FileHash -Algorithm SHA256 -LiteralPath '<game-folder>\RetailExe\1.2\cnc3ep1.dat'

A folder inside a Steam library is not sufficient
to establish the complete distribution provenance.

## Distribution inventory

| Distribution | Documented build | Local verification |
|---|---|---|
| Retail DVD | Official patch 1.02 | Not separately tested |
| Installed game executable | 1.02 binary | SHA256 verified |
| Steam | 1.03 reported for newer releases | Other binary not tested |
| EA App | 1.03 reported for newer releases | Not tested |
| Other / older builds | Build dependent | Not tested |

Versions in this table are research references,
not proof of compatibility with our own server.

## External sources

CNCNZ retail, Steam and EA App installation guide:
https://cncnz.com/features/technical-support-help-guides/installing-command-conquer-3-kanes-wrath/

CNCNZ version-launching guide:
https://cncnz.com/features/technical-support-help-guides/running-old-versions-of-cnc3-ra3/

Kane's Wrath community troubleshooting:
https://kaneswrath.com/kanes-wrath-troubleshooter/

## Compatibility conclusion

Validated for research:
- One local 1.02 executable identity and hash
- Reproducible game executable identification
- Distribution/build differences documented
- Untested cases explicitly identified

Not validated:
- EA App executable hashes
- Other Steam executable hashes
- Game 1.03 to custom server compatibility
- Real client to custom server compatibility

These untested compatibility cases must be
handled individually in future client support.

No proprietary executable has been copied.
No game patch or downgrade was performed.