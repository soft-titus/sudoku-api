# Changelog


## 1.0.0 - 2025-12-29
- feat: add github action
- feat: Initial commit



## 1.1.0 - 2025-12-29
- Merge pull request #1 from soft-titus/dev
- feat: add POST /puzzle endpoint



## 1.1.1 - 2025-12-29
- Merge pull request #2 from soft-titus/dev
- fix: support handling of CSVs
- fix: centralize S3 config and remove ingester-specific config
- fix: added PATCH /puzzle endpoint



## 1.1.2 - 2025-12-30
- Merge pull request #3 from soft-titus/dev
- fix: add DELETE /puzzle endpoint
- fix: add s3 health-check



## 1.2.0 - 2025-12-30
- Merge pull request #4 from soft-titus/dev
- feat: add GET /puzzle/{puzzle_id}/solution and GET /puzzle/{_puzzle_id}/puzzle endpoints
- fix: add GET /puzzle endpoint



## 1.2.1 - 2025-12-30
- Merge pull request #5 from soft-titus/dev
- fix: git hooks pre-commit should check all python files on the repo
- fix: use wrong env var for S3 credentials



## 1.2.2 - 2025-12-30
- Merge pull request #6 from soft-titus/dev
- fix: make all endpoints RESTful



## 1.2.3 - 2025-12-30
- fix: can't cache data from mongo, need to serialize it first



## 1.2.4 - 2025-12-30
- fix: can't cache to redis because of the datetime object
- fix: duplicate arguments, typo



## 1.2.5 - 2025-12-30
- Merge pull request #7 from soft-titus/dev
- fix: issue with fastapi streaming response

