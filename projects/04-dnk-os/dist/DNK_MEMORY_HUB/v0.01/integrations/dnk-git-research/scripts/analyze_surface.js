const fs = require('fs');
const path = require('path');

// --- Configuration ---
const LIB_PATH = path.join(__dirname, '../data/library.json');
const ENV_PATH = path.join(__dirname, '../.env');

// --- Utils ---
function loadEnv() {
  if (!fs.existsSync(ENV_PATH)) return {};
  const content = fs.readFileSync(ENV_PATH, 'utf8');
  const env = {};
  content.split('\n').forEach(line => {
    const [key, ...value] = line.split('=');
    if (key && value) env[key.trim()] = value.join('=').trim();
  });
  return env;
}

const env = loadEnv();
const GITHUB_TOKEN = env.GITHUB_TOKEN;

if (!GITHUB_TOKEN) {
  console.error('❌ Error: GITHUB_TOKEN not found in .env');
  process.exit(1);
}

// --- GraphQL Query ---
const QUERY = `
query RepoSurfaceAnalysis($owner: String!, $name: String!) {
  repository(owner: $owner, name: $name) {
    nameWithOwner
    url
    description
    primaryLanguage { name }
    stargazerCount
    forkCount
    watchers { totalCount }
    openIssues: issues(states: OPEN) { totalCount }
    openPRs: pullRequests(states: OPEN) { totalCount }
    licenseInfo { spdxId name }
    createdAt
    updatedAt
    pushedAt
    isArchived
    defaultBranchRef {
      target {
        ... on Commit {
          history(first: 1) {
            nodes { committedDate }
          }
        }
      }
    }
    releases(last: 1, orderBy: {field: CREATED_AT, direction: DESC}) {
      nodes {
        tagName
        publishedAt
      }
    }
    repositoryTopics(first: 10) {
      edges { node { topic { name } } }
    }
  }
}
`;

async function fetchRepoMetadata(owner, name) {
  const response = await fetch('https://api.github.com/graphql', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${GITHUB_TOKEN}`,
      'Content-Type': 'application/json',
      'User-Agent': 'DNK-Git-Research-Bot'
    },
    body: JSON.stringify({
      query: QUERY,
      variables: { owner, name }
    })
  });

  const result = await response.json();
  if (result.errors) {
    throw new Error(result.errors.map(e => e.message).join(', '));
  }
  return result.data.repository;
}

// --- Main ---
async function run(limit = 10) {
  console.log(`🚀 Starting surface analysis (limit: ${limit})...`);
  
  if (!fs.existsSync(LIB_PATH)) {
    console.error('❌ library.json not found');
    return;
  }

  const db = JSON.parse(fs.readFileSync(LIB_PATH, 'utf8'));
  const repoKeys = Object.keys(db.repos);
  
  let scannedCount = 0;
  
  for (const key of repoKeys) {
    if (scannedCount >= limit) break;
    
    const repo = db.repos[key];
    
    // Skip if already has metadata or if it's not a github repo
    if (repo.metadata && repo.status === 'metadata_scanned') continue;
    if (!repo.url.includes('github.com')) continue;

    try {
      // Parse owner and name from URL
      const urlParts = repo.url.replace(/\/$/, '').split('/');
      const name = urlParts.pop();
      const owner = urlParts.pop();

      if (!owner || !name || owner === 'github.com') {
          console.warn(`⚠️ Skipping invalid URL: ${repo.url}`);
          continue;
      }

      console.log(`🔍 Scanning ${owner}/${name}...`);
      const data = await fetchRepoMetadata(owner, name);
      
      // Update entry
      db.repos[key].metadata = {
        stars: data.stargazerCount,
        forks: data.forkCount,
        watchers: data.watchers.totalCount,
        open_issues: data.openIssues.totalCount,
        open_prs: data.openPRs.totalCount,
        primary_language: data.primaryLanguage ? data.primaryLanguage.name : null,
        topics: data.repositoryTopics.edges.map(e => e.node.topic.name),
        license: data.licenseInfo ? data.licenseInfo.spdxId : null,
        created_at: data.createdAt,
        updated_at: data.updatedAt,
        pushed_at: data.pushedAt,
        last_commit_date: data.defaultBranchRef ? data.defaultBranchRef.target.history.nodes[0].committedDate : null,
        latest_release_tag: data.releases.nodes[0] ? data.releases.nodes[0].tagName : null,
        is_archived: data.isArchived
      };
      
      db.repos[key].status = 'metadata_scanned';
      db.repos[key].analyzed_at = new Date().toISOString();
      
      scannedCount++;
      // Small delay to be polite to GitHub
      await new Promise(r => setTimeout(r, 500));

    } catch (err) {
      console.error(`❌ Failed to scan ${key}: ${err.message}`);
    }
  }

  if (scannedCount > 0) {
    fs.writeFileSync(LIB_PATH, JSON.stringify(db, null, 2));
    console.log(`✅ Successfully scanned ${scannedCount} repositories.`);
  } else {
    console.log('ℹ️ No repositories needed scanning.');
  }
}

// Get limit from args or default to 10
const limit = parseInt(process.argv[2]) || 10;
run(limit).catch(console.error);
