/**
 * UTR Player Scraper (Node.js version)
 * Scrapes tennis player info from UTR website based on predefined filters
 */

const https = require('https');

// ============================================
// USER PARAMETERS - CHANGE ME HERE
// ============================================
const args = process.argv.slice(2);

function getArg(flag, defaultValue) {
    const arg = args.find(a => a.startsWith(flag));
    return arg ? arg.split('=')[1] : defaultValue;
}

const PARAMS = {
    COUNTRY: getArg('--country', 'USA'),      // ISO-3 or 'ALL'
    GENDER: getArg('--gender', 'M'),          // 'M' or 'F'
    CATEGORY: getArg('--category', 'junior'), // 'junior', 'adult', 'all'
    TOP_COUNT: parseInt(getArg('--count', '100'), 10)
};
// ============================================

// Configuration derived from parameters
const CONFIG = {
    email: 'alberto.kuang@gmail.com',
    password: 'Spring2025',
    filters: {
        nationality: (PARAMS.COUNTRY === 'ALL' || PARAMS.COUNTRY === '') ? null : PARAMS.COUNTRY,
        gender: PARAMS.GENDER,
        minUtr: 1.0,
        maxUtr: 16.5,
        targetCount: PARAMS.TOP_COUNT
    }
};

// API URLs
const LOGIN_URL = 'https://app.utrsports.net/api/v1/auth/login';
const SEARCH_URL = 'https://app.utrsports.net/api/v2/search/players';

/**
 * Makes an HTTPS request
 */
function makeRequest(url, options = {}, postData = null) {
    return new Promise((resolve, reject) => {
        const urlObj = new URL(url);

        const requestOptions = {
            hostname: urlObj.hostname,
            path: urlObj.pathname + urlObj.search,
            method: options.method || 'GET',
            headers: {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                ...options.headers
            }
        };

        const req = https.request(requestOptions, (res) => {
            let data = '';

            res.on('data', chunk => data += chunk);
            res.on('end', () => {
                // Collect cookies from response
                const cookies = res.headers['set-cookie'] || [];

                try {
                    const jsonData = data ? JSON.parse(data) : {};
                    resolve({
                        status: res.statusCode,
                        data: jsonData,
                        cookies,
                        headers: res.headers
                    });
                } catch (e) {
                    resolve({
                        status: res.statusCode,
                        data: data,
                        cookies,
                        headers: res.headers
                    });
                }
            });
        });

        req.on('error', reject);

        if (postData) {
            req.write(JSON.stringify(postData));
        }

        req.end();
    });
}

/**
 * Login to UTR and get JWT token
 */
async function login(email, password) {
    console.log('🔐 Logging in to UTR...');

    const response = await makeRequest(LOGIN_URL, {
        method: 'POST'
    }, { email, password });

    if (response.status !== 200) {
        throw new Error(`Login failed with status ${response.status}: ${JSON.stringify(response.data)}`);
    }

    // Extract JWT token from cookies or response
    let token = response.data.jwt || response.data.token;

    // Check cookies for jwt token
    if (!token && response.cookies) {
        for (const cookie of response.cookies) {
            if (cookie.startsWith('jwt=')) {
                token = cookie.split('jwt=')[1].split(';')[0];
                break;
            }
        }
    }

    // Check Authorization header
    if (!token && response.headers.authorization) {
        token = response.headers.authorization.replace('Bearer ', '');
    }

    // Debug: show what we received
    console.log('📋 Login response cookies:', response.cookies);
    // console.log('📋 Login response headers:', Object.keys(response.headers));

    if (!token) {
        // The API might just use session cookies, let's try continuing with cookies
        console.log('⚠️  No JWT token found, will try using session cookies');
        return { cookies: response.cookies, data: response.data };
    }

    console.log('✅ Login successful! Token received.');
    return { token, cookies: response.cookies, data: response.data };
}

/**
 * Search for players based on filters
 */
async function searchPlayers(authInfo, filters) {
    const { nationality, gender, minUtr, maxUtr, top } = filters;
    const skip = filters.skip || 0;

    // Category specific: Junior vs Adult vs All
    let maxAge = null;
    let minAge = null;

    if (PARAMS.CATEGORY === 'junior') {
        maxAge = 18;
    } else if (PARAMS.CATEGORY === 'adult') {
        // minAge = 19; // Optional: Enforce min age logic if desired, API support varies
    }

    // Use URLSearchParams to safe-encode
    const params = new URLSearchParams();
    params.append('top', top);
    params.append('skip', skip);
    if (gender) params.append('gender', gender);
    if (nationality) params.append('nationality', nationality);
    if (minUtr) params.append('utrMin', minUtr);
    if (maxUtr) params.append('utrMax', maxUtr);
    params.append('utrType', 'verified');
    if (maxAge) params.append('maxAge', maxAge);
    if (minAge) params.append('minAge', minAge);

    const searchUrl = `${SEARCH_URL}?${params.toString()}`;

    console.log(`\n🔍 Searching URL: ${searchUrl}`);

    // Build headers with auth
    const headers = {};
    if (authInfo.token) {
        headers['Authorization'] = `Bearer ${authInfo.token}`;
    }
    if (authInfo.cookies && authInfo.cookies.length > 0) {
        headers['Cookie'] = authInfo.cookies.map(c => c.split(';')[0]).join('; ');
    }

    try {
        const response = await makeRequest(searchUrl, {
            method: 'GET',
            headers
        });

        if (response.status !== 200) {
            console.log(`Search Failed status: ${response.status}`);
            return { hits: [] };
        }

        // Debug total
        if (response.data && response.data.total) {
            console.log(`   API Total Matches: ${response.data.total}`);
        }

        return response.data;
    } catch (e) {
        console.log(`Search exception: ${e.message}`);
        return { hits: [] };
    }
}

const util = require('util');
const sleep = util.promisify(setTimeout);

/**
 * Get detailed player info including win/loss record from results summary
 */
async function getPlayerWinLoss(authInfo, playerId) {
    // We only need top=1 to get the summary stats { wins, losses }
    const resultsUrl = `https://app.utrsports.net/api/v1/player/${playerId}/results?top=1&skip=0`;

    // Auth headers
    const headers = {};
    if (authInfo.token) {
        headers['Authorization'] = `Bearer ${authInfo.token}`;
    }
    if (authInfo.cookies && authInfo.cookies.length > 0) {
        headers['Cookie'] = authInfo.cookies.map(c => c.split(';')[0]).join('; ');
    }

    try {
        const response = await makeRequest(resultsUrl, { headers });
        if (response.status === 200 && response.data) {
            return {
                wins: response.data.wins || 0,
                losses: response.data.losses || 0
            };
        }
    } catch (e) {
        // ignore error and return default
    }
    return { wins: 0, losses: 0 };
}

/**
 * Format and display results
 */
function displayResults(players) {
    const countryLabel = (PARAMS.COUNTRY === 'ALL' || PARAMS.COUNTRY === '') ? 'WORLD' : PARAMS.COUNTRY;
    const title = `${countryLabel} ${PARAMS.CATEGORY.toUpperCase()} ${PARAMS.GENDER === 'F' ? 'GIRLS' : 'BOYS'}`;
    console.log('\n' + '='.repeat(120));
    console.log(`🎾 ${title} (UTR > 1) - PLAYER LIST`);
    console.log('='.repeat(120));

    // Table header
    console.log(`\n${'#'.padEnd(3)} | ${'Name'.padEnd(25)} | ${'UTR'.padEnd(6)} | ${'Dbls'.padEnd(6)} | ${'Trend'.padEnd(8)} | ${'Age'.padEnd(4)} | ${'Location'.padEnd(20)} | ${'W/L'.padEnd(10)}`);
    console.log('-'.repeat(120));

    players.forEach((player, index) => {
        const num = String(index + 1).padEnd(3);
        const name = (player.name || 'Unknown').substring(0, 25).padEnd(25);
        const utr = String(player.utr || '-').padEnd(6);
        const dbls = String(player.doublesUtr || '-').padEnd(6);

        // Format trend with + or -
        let trendStr = '-';
        if (player.trend !== undefined && player.trend !== null) {
            const sign = player.trend > 0 ? '+' : '';
            trendStr = `${sign}${Number(player.trend).toFixed(2)}`;
        }
        const trend = trendStr.padEnd(8);

        const age = String(player.age || '-').padEnd(4);
        const location = (player.location || '-').substring(0, 20).padEnd(20);
        const winLoss = player.winLoss ? `${player.winLoss.wins}W-${player.winLoss.losses}L` : '-';

        console.log(`${num} | ${name} | ${utr} | ${dbls} | ${trend} | ${age} | ${location} | ${winLoss.padEnd(10)}`);
    });

    console.log('-'.repeat(120));
    console.log(`Total: ${players.length} players found\n`);
}

/**
 * Save results to CSV (Dynamic Filename)
 */
function saveToCSV(players) {
    const fs = require('fs');

    // Generate filename based on parameters and date
    // format: COUNTRY_CATEGORY_GENDER_YYYYMMDD.csv
    const date = new Date().toISOString().slice(0, 10).replace(/-/g, ''); // YYYYMMDD
    const genderStr = PARAMS.GENDER === 'M' ? 'Male' : (PARAMS.GENDER === 'F' ? 'Female' : 'All');
    const countryStr = (PARAMS.COUNTRY === 'ALL' || PARAMS.COUNTRY === '') ? 'World' : PARAMS.COUNTRY;
    const filename = `${countryStr}_${PARAMS.CATEGORY}_${genderStr}_${date}.csv`;

    const headers = [
        'Rank', 'Name', 'Singles UTR', 'Doubles UTR', '3-Month Trend',
        'Age', 'Location',
        'Wins', 'Losses', 'Win Rate', 'Profile URL'
    ];

    const rows = players.map((p, i) => {
        const wins = p.winLoss?.wins || 0;
        const losses = p.winLoss?.losses || 0;
        const total = wins + losses;
        const winRate = total > 0 ? ((wins / total) * 100).toFixed(1) + '%' : '-';
        const trend = p.trend !== undefined && p.trend !== null ? Number(p.trend).toFixed(2) : '';

        return [
            i + 1,
            `"${p.name || ''}"`,
            p.utr || '',
            p.doublesUtr || '',
            trend,
            p.age || '',
            `"${p.location || ''}"`,
            wins,
            losses,
            winRate,
            p.profileUrl || ''
        ].join(',');
    });

    const csv = [headers.join(','), ...rows].join('\n');
    fs.writeFileSync(filename, csv, 'utf8');
    console.log(`📁 Results saved to: ${filename}`);
}

/**
 * Main function
 */
async function main() {
    console.log('================================================================');
    console.log('          UTR PLAYER SCRAPER');
    console.log('================================================================\n');
    console.log(`Parameters: Country=${PARAMS.COUNTRY}, Gender=${PARAMS.GENDER}, Category=${PARAMS.CATEGORY}, Top=${PARAMS.TOP_COUNT}\n`);

    try {
        // Step 1: Login
        const authInfo = await login(CONFIG.email, CONFIG.password);

        let skippedCount = 0;
        const targetCount = PARAMS.TOP_COUNT;
        const players = [];

        // UTR Bands to bypass 100-result limit
        const utrBands = [
            { min: 11, max: 16.5 },
            { min: 10, max: 11 },
            { min: 9, max: 10 },
            { min: 8, max: 9 },
            { min: 7, max: 8 },
            { min: 6, max: 7 },
            { min: 4, max: 6 },
            { min: 1, max: 4 }
        ];

        console.log(`Target: ${targetCount} confirmed players`);
        console.log('Using UTR Banding strategy to find more players...');

        const seenIds = new Set();
        const seenNames = new Set();

        for (const band of utrBands) {
            if (players.length >= targetCount) break;

            console.log(`\n🔍 Scanning UTR Band: ${band.min} - ${band.max}...`);

            // Search this band (Top 100 is max per query)
            const bandFilters = {
                ...CONFIG.filters,
                top: 100,
                skip: 0,
                minUtr: band.min,
                maxUtr: band.max
            };

            const searchResults = await searchPlayers(authInfo, bandFilters);
            const hits = searchResults.hits || searchResults.players || [];

            if (hits.length === 0) {
                console.log('   No results in this band.');
                continue;
            }

            console.log(`   Found ${hits.length} raw results. Filtering...`);
            let addedInBand = 0;

            for (const hit of hits) {
                if (players.length >= targetCount) break;

                const source = hit.source || hit;

                // Deduplicate by ID
                if (seenIds.has(source.id)) continue;

                // Deduplicate by Name
                const candidateName = source.displayName || `${source.firstName} ${source.lastName}`;
                if (seenNames.has(candidateName)) continue;

                const ageRange = source.ageRange || '';
                const age = source.age;

                // Category Filtering logic
                if (PARAMS.CATEGORY === 'junior') {
                    // Strict Junior Filter (<= 18)
                    // Exclude if explicitly older than 18
                    if (age && age > 18) {
                        skippedCount++;
                        continue;
                    }
                    // If age is null, check ageRange
                    if (!age && ageRange) {
                        if (ageRange.startsWith('19') || ageRange.startsWith('2') || ageRange.startsWith('3') || ageRange.startsWith('4') || ageRange.startsWith('5')) {
                            skippedCount++;
                            continue;
                        }
                    }
                } else if (PARAMS.CATEGORY === 'adult') {
                    // Adult Filter (> 18 or explicitly not junior)
                    if (age && age <= 18) {
                        skippedCount++;
                        continue;
                    }
                    if (!age && ageRange) {
                        if (ageRange.includes('14-18') || ageRange.includes('16-18')) {
                            skippedCount++;
                            continue;
                        }
                    }
                }

                // Fetch Win/Loss
                const winLoss = await getPlayerWinLoss(authInfo, source.id);

                // Extract new metrics
                const doublesUtr = source.doublesUtr || source.myUtrDoubles || source.utrDoubles;
                const trend = source.threeMonthRatingChangeDetails?.ratingDifference;

                // Add slight delay
                await sleep(50);
                process.stdout.write('.');

                const player = {
                    id: source.id,
                    name: source.displayName || `${source.firstName} ${source.lastName}`,
                    utr: source.singlesUtr || source.myUtrSingles || source.utrSingles,
                    doublesUtr: doublesUtr,
                    trend: trend,
                    age: source.age || ageRange || '-',
                    location: source.location?.display || source.city || '',
                    nationality: source.nationality,
                    profileUrl: `https://app.utrsports.net/profiles/${source.id}`,
                    winLoss: winLoss
                };

                seenIds.add(player.id);
                seenNames.add(player.name);
                players.push(player);
                addedInBand++;
            }
            console.log(`\n   Added ${addedInBand} valid players from this band.`);
            console.log(`   Total Progress: ${players.length}/${targetCount}`);
        }


        // Sort by UTR descending
        players.sort((a, b) => (b.utr || 0) - (a.utr || 0));

        // Step 4: Display results
        displayResults(players);

        // Step 5: Save to CSV
        saveToCSV(players);

    } catch (error) {
        console.error('\n❌ Error:', error.message);
        process.exit(1);
    }
}

// Run the scraper
main();
