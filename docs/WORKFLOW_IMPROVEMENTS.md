# GitHub Actions Workflow Improvements (Historical)

## Summary of Changes

Note: This document contains historical workflow work. Several workflows referenced below were intentionally removed during repository slimming.

All GitHub Actions workflows have been reviewed and updated to address validation errors and improve robustness.

## Issues Fixed

### 1. Secret Access Validation (Critical)

**Problem**: Workflows were accessing secrets without checking if they exist, causing "Context access might be invalid" warnings and potential runtime failures.

**Solution**: Added validation steps before accessing secrets:

#### `news-sentiment-refresh.yml`
- Added `Validate API Key` step to check if `NEWS_API_KEY` exists
- Workflow gracefully skips sentiment analysis if API key is missing
- Clear warning messages guide users to configure required secrets

#### Airflow workflows
- Airflow-specific workflows were later removed from this repository as non-critical.

### 2. Schedule Event Conditionals

**Problem**: `database-optimization.yml` used incorrect syntax for schedule-based conditionals (`github.event.schedule == '...'`)

**Solution**: 
- Changed to proper event_name checks: `github.event_name == 'schedule' && github.event.schedule == '...'`
- Added fallback to run on `workflow_dispatch` for manual testing
- Both snapshot and cleanup jobs now have correct conditional logic

### 3. Environment Configuration

**Problem**: Legacy environment-specific CI workflow complexity.

**Solution**:
- Consolidated onto core workflows and removed non-critical pipeline variants.

### 4. Docker Image Naming (Critical)

**Problem**: Docker registry requires lowercase repository names, but `Economic-Dashboard-API` contains uppercase letters, causing build failures:
```
ERROR: invalid tag "ghcr.io/moshesham/Economic-Dashboard-API-worker:latest": 
repository name must be lowercase
```

**Solution**: `docker.yml`
- Added `Prepare image name` step to convert repository name to lowercase using `tr '[:upper:]' '[:lower:]'`
- Applied to both main image and worker image builds
- Updated deployment summary to use lowercase image names
- Images now build successfully as `ghcr.io/moshesham/economic-dashboard-api:latest`

### 5. Git Push Permissions (Critical)

**Problem**: Workflows that commit and push data changes were failing with:
```
remote: Permission to moshesham/Economic-Dashboard-API.git denied to github-actions[bot].
fatal: unable to access 'https://github.com/...': The requested URL returned error: 403
```

**Solution**: Multiple workflows updated
- Added `permissions: contents: write` at workflow level
- Added `persist-credentials: true` to all `actions/checkout@v4` steps
- Ensures `GITHUB_TOKEN` has permission to push commits

**Affected workflows**:
- `data-refresh.yml` - Daily data refresh commits
- `news-sentiment-refresh.yml` - Sentiment data commits
- `database-optimization.yml` - Snapshot and cleanup commits

### 6. Concurrent Push Race Conditions (Critical)

**Problem**: Multiple workflows running simultaneously were failing to push with:
```
error: failed to push some refs to 'https://github.com/...'
hint: Updates were rejected because the remote contains work that you do not
hint: have locally. This is usually caused by another repository pushing to
hint: the same ref.
```

**Solution**: Implemented pull-rebase-retry logic
- Pull latest changes with `git pull --rebase` before pushing
- Automatic conflict resolution (prefer workflow's changes for data files)
- Retry logic with exponential backoff (3 attempts max)
- Clear success/failure messages

**Implementation**:
```bash
MAX_RETRIES=3
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
  git pull --rebase origin main || {
    # Auto-resolve conflicts preferring our data
    git checkout --ours data/
    git add data/
    git rebase --continue
  }
  
  if git push origin main; then
    exit 0  # Success
  else
    sleep $((2 ** RETRY_COUNT))  # Exponential backoff
  fi
done
```

**Affected workflows**:
- `data-refresh.yml` - Daily data commits
- `news-sentiment-refresh.yml` - Sentiment data commits
- `database-optimization.yml` - Monthly archive commits

## Workflow Status

| Workflow | Status | Notes |
|----------|--------|-------|
| `ci.yml` | ✅ Active | Primary CI checks |
| `security.yml` | ✅ Active | Security scanning |
| `docker.yml` | ✅ Active | Image build/publish |
| `release.yml` | ✅ Active | Tagged release pipeline |
| `deploy-docker.yml` | ✅ Active | Deployment workflow |
| `data-refresh.yml` | ✅ Active | Scheduled refresh |
| `news-sentiment-refresh.yml` | ✅ Active | Optional secret-gated sentiment refresh |
| `database-optimization.yml` | ✅ Active | Snapshot/cleanup automation |

## Required Repository Secrets

To enable all workflow features, configure these secrets in repository settings:

### Data & Analysis
- `NEWS_API_KEY` - For news sentiment analysis workflow

### Airflow Integration
- `AIRFLOW_URL` - Airflow server URL (e.g., https://your-airflow.com)
- `AIRFLOW_USERNAME` - Airflow API username
- `AIRFLOW_PASSWORD` - Airflow API password
- `AIRFLOW_SSH_HOST` - Airflow server SSH host (for DAG deployment)
- `AIRFLOW_SSH_USER` - SSH username
- `AIRFLOW_SSH_KEY` - SSH private key
- `AIRFLOW_DAGS_FOLDER` - DAG folder path (default: ~/airflow/dags)

### Cloud Deployments (Optional)
- `ASTRONOMER_API_KEY` - For Astronomer.io deployments
- `GCP_PROJECT` - Google Cloud project ID
- `GCP_COMPOSER_BUCKET` - Cloud Composer bucket name
- `GCP_SERVICE_ACCOUNT_KEY` - GCP service account JSON key

## Testing Workflows

All workflows can be tested manually via `workflow_dispatch`:

```bash
# Trigger any workflow manually from GitHub UI
# Actions > Select workflow > Run workflow
```

### Testing Checklist
- [ ] Configure required secrets for workflows you plan to use
- [ ] Test manual workflow triggers
- [ ] Verify workflows skip gracefully when secrets are missing
- [ ] Check workflow summary outputs for helpful error messages

## Best Practices Implemented

1. **Graceful Degradation**: Workflows skip unavailable features instead of failing
2. **Clear Messaging**: Warning messages guide users to configure missing secrets
3. **Fail-Safe Conditionals**: Multiple fallback conditions for robust execution
4. **Manual Override**: All scheduled workflows support manual triggering
5. **Informative Summaries**: Workflow summaries show status and configuration state

## Next Steps

1. **Configure Secrets**: Add required secrets to repository settings based on your infrastructure
2. **Enable Environments**: Create `development` and `production` environments in repository settings for deployment protection
3. **Test Workflows**: Manually trigger each workflow to verify configuration
4. **Monitor Runs**: Check Actions tab for workflow execution logs and summaries

## Related Documentation

- GitHub Actions secrets: https://docs.github.com/en/actions/security-guides/encrypted-secrets
- Repository environments: https://docs.github.com/en/actions/deployment/targeting-different-environments/using-environments-for-deployment
- Workflow syntax: https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions
