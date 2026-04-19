# UF Shands — Warning Banner for Distribution Recipient

## Context
- **Customer:** UF Health / Shands (University of Florida)
- **Contact:** Craig S. Gorme (gormec@shands.ufl.edu)
- **Trend TA:** Austin Bowling (TS-NA)
- **Subject:** Email & Collaboration Security doc - Correlated Intelligence - Warning Banner
- **Email thread:** Dec 12, 2025
- **Also involved:** Cristian A. Prano

## What We Know
- This is about Correlated Intelligence warning banners in CECP/CEGP
- UF Health has their own external email warning banner ("CAUTION! This email came from outside UF or UF Health")
- Issue appears to be about how warning banners interact with distribution list recipients
- Joel's card says "test warning banner for distro recipient" — likely testing whether the banner correctly applies when email goes to a distribution list vs individual recipient

## Research Needed
- [ ] Read the actual email thread in full (need to get message ID and pull via Graph API)
- [ ] Check CECP documentation on warning banner behavior for distribution lists
- [ ] Test in a lab environment if possible
- [ ] Check if this is a known issue/feature request

## Related
- Correlated Intelligence is the same feature Matt Patterson at Panavision was discussing
- Warning banners are inserted by CECP into email body for suspicious/external emails
