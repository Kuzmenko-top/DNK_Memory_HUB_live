const fs = require('fs');
const path = require('path');
const BASE_PATH = path.resolve(__dirname, '..');
const LIBRARY_PATH = path.join(BASE_PATH, "data/library.json");
const AUDIT_TABLE_PATH = path.join(BASE_PATH, "data/DNK_Repo_AUDIT/AUDIT_SUMMARY_TABLE.md");
const RAW_LIST_PATH = path.join(BASE_PATH, "data/raw_github_list.txt");

function extractUrl(text) {
    if (!text) return null;
    const urlMatch = text.match(/https:\/\/github\.com\/[^\s\|<>\)]+/);
    return urlMatch ? urlMatch[0].replace(/\/$/, '') : null;
}

function parseAuditTable(filePath) {
    if (!fs.existsSync(filePath)) return [];
    const content = fs.readFileSync(filePath, 'utf-8');
    const lines = content.split('\n');
    const repos = [];
    
    for (const line of lines) {
        if (line.includes('|') && !line.includes('---') && line.toLowerCase().includes('github.com')) {
            const parts = line.split('|').map(p => p.trim());
            if (parts.length >= 2) {
                // Try to find URL in any part, but usually it's in part 1 or part 5
                let url = extractUrl(line);
                if (url) {
                    repos.push({ 
                        name: parts[1] || "Unknown", 
                        desc: parts[2] || "", 
                        license: parts[3] || "", 
                        role: parts[4] || "", 
                        url 
                    });
                }
            }
        }
    }
    return repos;
}

function consolidate() {
    console.log("Starting consolidation...");
    
    let library = { repos: {} };
    if (fs.existsSync(LIBRARY_PATH)) {
        try {
            library = JSON.parse(fs.readFileSync(LIBRARY_PATH, 'utf-8'));
        } catch (e) {
            console.error("Error parsing library.json, starting fresh.");
        }
    }
    
    const auditRepos = parseAuditTable(AUDIT_TABLE_PATH);
    console.log(`Found ${auditRepos.length} repos in audit table.`);
    
    const rawUrls = fs.existsSync(RAW_LIST_PATH) ? fs.readFileSync(RAW_LIST_PATH, 'utf-8').split('\n').map(l => l.trim()).filter(l => l) : [];
    console.log(`Found ${rawUrls.length} raw URLs.`);
    
    let addedCount = 0;
    let updatedCount = 0;
    
    const processRepo = (url, name, desc, license, role) => {
        const urlParts = url.split('github.com/');
        if (urlParts.length < 2) return;
        const fullName = urlParts[1].toUpperCase();
        if (!fullName || fullName === "") return;
        
        if (!library.repos[fullName]) {
            library.repos[fullName] = {
                full_name: fullName,
                name: name || fullName.split('/').pop(),
                url: url,
                summary_ua: desc || "",
                license: license || "unknown",
                dnk_role: role || "",
                status: "pending_scan",
                saved_at: new Date().toISOString()
            };
            addedCount++;
        } else {
            const repo = library.repos[fullName];
            if (desc && !repo.summary_ua) repo.summary_ua = desc;
            if (role && !repo.dnk_role) repo.dnk_role = role;
            if (license && license !== "unknown") repo.license = license;
            updatedCount++;
        }
    };

    // Process audit table first
    for (const ar of auditRepos) {
        processRepo(ar.url, ar.name, ar.desc, ar.license, ar.role);
    }
    
    // Process raw list
    for (const url of rawUrls) {
        processRepo(url.replace(/\/$/, ''), null, null, null, null);
    }
    
    console.log(`Consolidation complete. Total unique repos: ${Object.keys(library.repos).length}`);
    console.log(`Added: ${addedCount}, Updated: ${updatedCount}`);
    
    fs.writeFileSync(LIBRARY_PATH, JSON.stringify(library, null, 2), 'utf-8');
    console.log(`Saved consolidated library to ${LIBRARY_PATH}`);
}

consolidate();
