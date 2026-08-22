# MovieLens 100K rights and release record

Retrieval date: 2026-08-23 (Asia/Saigon)  
Stage: R6-D1, proposal and source research only

## Provider and release

The current official authority is the GroupLens Research Project at the University of Minnesota. GroupLens identifies MovieLens as the source service and provides the release metadata and download surfaces. The [official MovieLens 100K page](https://grouplens.org/datasets/movielens/100k/) classifies this release as a stable benchmark and dates it to April 1998.

The release-specific [official README](https://files.grouplens.org/datasets/movielens/ml-100k-README.txt) gives the exact contents: 100,000 ratings by 943 users on 1,682 movies, with every included user having at least 20 ratings. It dates collection from 19 September 1997 through 22 April 1998. The landing page's “1000 users” and “1700 movies” are treated as rounded display values, not exact cardinalities; the official [u.info](https://files.grouplens.org/datasets/movielens/ml-100k/u.info) confirms 943 users, 1,682 items, and 100,000 ratings.

The canonical archive locator is [ml-100k.zip](https://files.grouplens.org/datasets/movielens/ml-100k.zip). A headers-only request returned HTTP 200 without a redirect and advertised 4,924,029 bytes. The current official [checksum sidecar](https://files.grouplens.org/datasets/movielens/ml-100k.zip.md5) returned the exact line `MD5 (ml-100k.zip) = 0e33842e24a9c977be4e0107933c0723`. The archive itself was not downloaded, so that MD5 has not yet been recomputed against acquired archive bytes. No official SHA-256 was found; later materialization must compute and retain a local SHA-256 without presenting it as a historical provider checksum.

## Access, use, redistribution, and acknowledgment

These are four separate facts, all governed by the current official surfaces:

- Access: the landing page, README, archive, checksum, and [unzipped file index](https://files.grouplens.org/datasets/movielens/ml-100k/) were publicly reachable without authentication during this retrieval. Public reachability does not itself grant redistribution or commercial rights.

- Research use: the README says the dataset “may be used for any research purposes,” subject to its listed conditions. It also disclaims guarantees concerning correctness, suitability, and validity of resulting work.

- Redistribution: the README says users “may not redistribute the data without separate permission.” The current [MovieLens catalog](https://grouplens.org/datasets/movielens/) reinforces that public redistribution is typically not permitted and directs permission seekers to read the README and use the provider's request route.

- Commercial or revenue-bearing use: prior permission from a GroupLens faculty member at the University of Minnesota is required under the README terms.

- Acknowledgment and non-endorsement: publications must acknowledge dataset use, and users may not state or imply endorsement by the University of Minnesota or GroupLens. The README's requested publication citation is F. Maxwell Harper and Joseph A. Konstan, “The MovieLens Datasets: History and Context,” ACM TiiS 5(4), Article 19 (2015), DOI 10.1145/2827872.

## License characterization

The README labels its section “SUMMARY & USAGE LICENSE” and supplies provider-authored conditions. The inspected official surfaces do not identify a standard SPDX, Creative Commons, or other named open-data license for MovieLens 100K. This record therefore classifies the governing text as custom provider usage terms, not as an unrestricted open license. That classification does not replace legal review or provider permission where redistribution, commercial use, or another unlisted use is contemplated.

The RecBole MIT code license does not apply to MovieLens data. Likewise, RecBole's S3 processed archive, repository atomic files, mirrors, search snippets, and package caches do not supply GroupLens rights authority.

## Release-file scope

The official index exposes 23 release files: `README`, `allbut.pl`, `mku.sh`, `u.data`, `u.genre`, `u.info`, `u.item`, `u.occupation`, `u.user`, the ten `u1`–`u5` base/test files, and the four `ua`/`ub` base/test files. Later extraction must accept exactly this logical inventory under the archive's single release directory and fail on additions, omissions, duplicate paths, traversal paths, links, or reparse points.

## Current boundary

No dataset archive was downloaded or written, no file was extracted or converted, and no RecBole, training, evaluation, tuning, checkpoint, harmonized-v5, or project TEST action occurred. Rights-sensitive redistribution remains prohibited unless separate GroupLens permission is recorded.
