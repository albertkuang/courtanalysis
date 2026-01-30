/**
 * UTR Player Scraper - Multi-Country Merge Version
 * Searches multiple countries and merges results to get TRUE global top juniors
 */

const https = require('https');
const fs = require('fs');

// ============================================
// ARGUMENT PARSING
// ============================================
const args = process.argv.slice(2);

function getArg(flag, defaultValue) {
    const index = args.findIndex(a => a === flag || a.startsWith(flag + '='));
    if (index === -1) return defaultValue;
    const arg = args[index];
    if (arg.includes('=')) return arg.split('=')[1] || defaultValue;
    const nextArg = args[index + 1];
    if (nextArg && !nextArg.startsWith('--')) return nextArg;
    return defaultValue;
}

const PARAMS = {
    COUNTRY: getArg('--country', 'USA'),
    GENDER: getArg('--gender', 'M'),
    CATEGORY: getArg('--category', 'junior'),
    TOP_COUNT: parseInt(getArg('--count', '100'), 10) || 100,
    HISTORY: args.includes('--history')
};

// Major tennis countries to search when using --country=MAJOR
const MAJOR_TENNIS_COUNTRIES = [
    'USA', 'CAN', 'GBR', 'AUS', 'FRA', 'DEU', 'ESP', 'ITA', 'JPN', 'CHN',
    'RUS', 'CZE', 'SRB', 'POL', 'NLD', 'BEL', 'SWE', 'AUT', 'SVK', 'UKR',
    'BRA', 'ARG', 'MEX', 'KOR', 'IND', 'NZL', 'ZAF', 'ISR', 'TUR', 'GRC',
    'ROU', 'HUN', 'PRT', 'CHE', 'BGR', 'HRV', 'SVN', 'LUX', 'THA', 'TWN'
];

const CONFIG = {
    email: 'alberto.kuang@gmail.com',
    password: 'Spring2025'
};

const LOGIN_URL = 'https://app.utrsports.net/api/v1/auth/login';
const SEARCH_URL = 'https://app.utrsports.net/api/v2/search/players';

// ============================================
// HTTP REQUEST HELPER
// ============================================
function makeRequest(url, options = {}, postData = null) {
    return new Promise((resolve, reject) => {
        const urlObj = new URL(url);
        const requestOptions = {
            hostname: urlObj.hostname,
            path: urlObj.pathname + urlObj.search,
            method: options.method || 'GET',
            headers: {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0',
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                ...options.headers
            }
        };

        const req = https.request(requestOptions, (res) => {
            let data = '';
            res.on('data', chunk => data += chunk);
            res.on('end', () => {
                try {
                    resolve({
                        status: res.statusCode,
                        data: data ? JSON.parse(data) : {},
                        cookies: res.headers['set-cookie'] || []
                    });
                } catch (e) {
                    resolve({ status: res.statusCode, data, cookies: [] });
                }
            });
        });
        req.on('error', reject);
        if (postData) req.write(JSON.stringify(postData));
        req.end();
    });
}

// ============================================
// LOGIN
// ============================================
async function login() {
    console.log('🔐 Logging in to UTR...');
    const response = await makeRequest(LOGIN_URL, { method: 'POST' }, {
        email: CONFIG.email,
        password: CONFIG.password
    });

    if (response.status !== 200) throw new Error('Login failed');

    let token = response.data.jwt || response.data.token;
    if (!token) {
        for (const cookie of response.cookies) {
            if (cookie.startsWith('jwt=')) {
                token = cookie.split('jwt=')[1].split(';')[0];
                break;
            }
        }
    }
    console.log('✅ Login successful!');
    return { token, cookies: response.cookies };
}

// ============================================
// SEARCH PLAYERS
// ============================================
async function searchPlayers(authInfo, filters) {
    const params = new URLSearchParams();
    params.append('top', filters.top || 100);
    params.append('skip', filters.skip || 0);
    if (filters.gender) params.append('gender', filters.gender);
    if (filters.nationality) params.append('nationality', filters.nationality);
    if (filters.minUtr) params.append('utrMin', filters.minUtr);
    if (filters.maxUtr) params.append('utrMax', filters.maxUtr);
    params.append('utrType', 'verified');
    // Use ageTags for junior filtering (matches UTR API)
    if (filters.ageTags) params.append('ageTags', filters.ageTags);

    const url = `${SEARCH_URL}?${params.toString()}`;

    const headers = {};
    if (authInfo.token) headers['Authorization'] = `Bearer ${authInfo.token}`;
    if (authInfo.cookies?.length) {
        headers['Cookie'] = authInfo.cookies.map(c => c.split(';')[0]).join('; ');
    }

    const response = await makeRequest(url, { headers });
    return response.status === 200 ? response.data : { hits: [] };
}

// ============================================
// EXTRACT PLAYER DATA
// ============================================
function extractPlayer(source) {
    const ageRange = source.ageRange || '';
    const age = source.age;

    // Pro Rank
    let proRank = '-';
    if (source.thirdPartyRankings?.length) {
        const rankObj = source.thirdPartyRankings.find(r => r.source === 'ATP' || r.source === 'WTA') || source.thirdPartyRankings[0];
        if (rankObj) proRank = `${rankObj.source} #${rankObj.rank}`;
    }

    // College
    let college = '-';
    if (source.playerCollege) {
        college = typeof source.playerCollege === 'object' ? source.playerCollege.name || '-' : String(source.playerCollege);
    } else if (source.collegeRecruiting) {
        college = 'Recruiting';
    }

    // Age display
    let ageDisplay = age || ageRange || '-';
    if (source.birthDate) {
        const year = source.birthDate.split('-')[0];
        ageDisplay = `${year} (${ageDisplay})`;
    }

    return {
        id: source.id,
        name: source.displayName || `${source.firstName} ${source.lastName}`,
        utr: source.singlesUtr || source.myUtrSingles || 0,
        doublesUtr: source.doublesUtr || source.myUtrDoubles || '',
        trend: source.threeMonthRatingChangeDetails?.ratingDifference,
        age: ageDisplay,
        rawAge: age,
        ageRange: ageRange,
        location: source.location?.display || source.city || '',
        nationality: source.nationality,
        proRank,
        college,
        profileUrl: `https://app.utrsports.net/profiles/${source.id}`,
        yearDelta: null // To be filled later if history is requested
    };
}

// ============================================
// FETCH PLAYER HISTORY (1 YEAR DELTA)
// ============================================
async function fetchPlayerDelta(authInfo, player) {
    try {
        const types = ['verified', 'myutr'];
        let history = [];

        for (const rType of types) {
            const statsUrl = `https://app.utrsports.net/api/v1/player/${player.id}/stats?type=singles&resultType=${rType}&Months=12`;
            const headers = {};
            if (authInfo.token) headers['Authorization'] = `Bearer ${authInfo.token}`;
            if (authInfo.cookies?.length) {
                headers['Cookie'] = authInfo.cookies.map(c => c.split(';')[0]).join('; ');
            }

            const response = await makeRequest(statsUrl, { headers });
            if (response.status === 200) {
                const resData = response.data;
                const historyArr = resData?.extendedRatingProfile?.history || resData?.ratingHistory;
                if (historyArr && historyArr.length > 0) {
                    history = historyArr;
                    break;
                }
            }
        }

        if (history && history.length > 0) {
            const currentRating = player.utr;
            const oneYearAgo = new Date();
            oneYearAgo.setDate(oneYearAgo.getDate() - 365);

            let priorRating = null;
            let closestDiff = Infinity;

            for (const entry of history) {
                const entryDate = new Date(entry.date);
                const diff = Math.abs(entryDate.getTime() - oneYearAgo.getTime());
                if (diff < closestDiff) {
                    closestDiff = diff;
                    priorRating = entry.rating;
                }
            }

            const maxDiff = 60 * 24 * 60 * 60 * 1000; // Allow 60 days diff for safety
            if (priorRating !== null && priorRating > 0 && closestDiff < maxDiff) {
                player.yearDelta = parseFloat((currentRating - priorRating).toFixed(2));
            }
        }
    } catch (e) { }
}

// ============================================
// MAIN FUNCTION
// ============================================
async function main() {
    console.log('================================================================');
    console.log('          UTR PLAYER SCRAPER (Multi-Country Merge)');
    console.log('================================================================');
    console.log(`Country=${PARAMS.COUNTRY}, Gender=${PARAMS.GENDER}, Category=${PARAMS.CATEGORY}, Count=${PARAMS.TOP_COUNT}\n`);

    const authInfo = await login();
    const targetCount = PARAMS.TOP_COUNT;
    const allPlayers = [];
    const seenIds = new Set();

    // Determine search mode: ALL (global), MAJOR (40 countries), or specific country
    const isGlobalSearch = PARAMS.COUNTRY === 'ALL' || PARAMS.COUNTRY === '';
    const isMajorSearch = PARAMS.COUNTRY === 'MAJOR';
    const countriesToSearch = isMajorSearch
        ? MAJOR_TENNIS_COUNTRIES
        : (isGlobalSearch ? [null] : [PARAMS.COUNTRY]);  // null = no nationality filter (global)

    if (isGlobalSearch) {
        console.log(`Searching GLOBALLY (all countries) for top juniors...\n`);
    } else if (isMajorSearch) {
        console.log(`Searching ${MAJOR_TENNIS_COUNTRIES.length} major tennis countries...\n`);
    } else {
        console.log(`Searching country: ${PARAMS.COUNTRY}...\n`);
    }

    for (const country of countriesToSearch) {
        if (country) {
            process.stdout.write(`🔍 ${country}... `);
        } else {
            process.stdout.write(`🌍 Global search... `);
        }

        // Use UTR banding to get more results
        const utrBands = [
            { min: 10, max: 16.5 },
            { min: 9, max: 10 },
            { min: 8, max: 9 },
            { min: 7, max: 8 },
            { min: 6, max: 7 },
            { min: 5, max: 6 },
            { min: 1, max: 5 }
        ];

        let countryAdded = 0;

        for (const band of utrBands) {
            const filters = {
                nationality: country,  // null = no filter (global search)
                gender: PARAMS.GENDER,
                minUtr: band.min,
                maxUtr: band.max,
                ageTags: PARAMS.CATEGORY === 'junior' ? 'U18' : null,
                top: 100
            };

            const results = await searchPlayers(authInfo, filters);
            const hits = results.hits || results.players || [];

            for (const hit of hits) {
                const source = hit.source || hit;
                if (seenIds.has(source.id)) continue;

                const player = extractPlayer(source);

                // Note: API already filters by maxAge=18 for juniors
                // No additional client-side age filtering needed

                seenIds.add(source.id);
                allPlayers.push(player);
                countryAdded++;
            }
        }

        console.log(`${countryAdded} players`);
    }

    // Sort ALL players by UTR descending
    allPlayers.sort((a, b) => (b.utr || 0) - (a.utr || 0));

    // Limit to top list before fetching history
    const finalPlayers = allPlayers.slice(0, targetCount);

    // Fetch 1-year history if requested
    if (PARAMS.HISTORY) {
        console.log(`\n⏳ Fetching 1-year history for top ${finalPlayers.length} players...`);
        // Process in batches of 5 to avoid hammering the API
        const batchSize = 5;
        for (let i = 0; i < finalPlayers.length; i += batchSize) {
            const batch = finalPlayers.slice(i, i + batchSize);
            process.stdout.write(`\rProgress: ${i}/${finalPlayers.length}    `);
            await Promise.all(batch.map(p => fetchPlayerDelta(authInfo, p)));
        }
        console.log(`\r✅ History fetch complete.                    \n`);
    }

    console.log(`\n✅ Collected ${allPlayers.length} total players, selecting top ${finalPlayers.length}`);

    // Display results
    console.log('\n' + '='.repeat(100));
    console.log(`🎾 TOP ${finalPlayers.length} ${PARAMS.CATEGORY.toUpperCase()} ${PARAMS.GENDER === 'F' ? 'GIRLS' : 'BOYS'} (${PARAMS.COUNTRY === 'ALL' ? 'WORLD' : PARAMS.COUNTRY})`);
    console.log('='.repeat(100));

    finalPlayers.slice(0, 20).forEach((p, i) => {
        const deltaStr = p.yearDelta !== null ? (p.yearDelta > 0 ? `+${p.yearDelta}` : p.yearDelta) : '-';
        console.log(`${String(i + 1).padStart(3)}. ${p.name.substring(0, 25).padEnd(25)} UTR: ${String(p.utr).padEnd(6)} ${(p.nationality || '').padEnd(4)} 1Y: ${String(deltaStr).padEnd(6)} ${p.proRank.padEnd(12)}`);
    });
    if (finalPlayers.length > 20) console.log(`    ... and ${finalPlayers.length - 20} more`);

    // Save CSV
    const date = new Date().toISOString().slice(0, 10).replace(/-/g, '');
    const countryStr = (PARAMS.COUNTRY === 'ALL' || PARAMS.COUNTRY === '') ? 'World' : PARAMS.COUNTRY;
    const genderStr = PARAMS.GENDER === 'M' ? 'Male' : 'Female';
    const filename = `${countryStr}_${PARAMS.CATEGORY}_${genderStr}_ANALYST_${date}.csv`;

    const headers = ['Rank', 'Name', 'Singles UTR', 'Doubles UTR', '3-Month Trend', '1-Year Delta', 'Age', 'Country', 'Location', 'Pro Rank', 'College', 'Profile URL'];
    const rows = finalPlayers.map((p, i) => [
        i + 1,
        `"${p.name}"`,
        p.utr,
        p.doublesUtr,
        p.trend !== undefined && p.trend !== null ? p.trend.toFixed(2) : '',
        p.yearDelta !== null ? p.yearDelta : '',
        p.age,
        p.nationality || '',
        `"${p.location}"`,
        p.proRank,
        `"${p.college}"`,
        p.profileUrl
    ].join(','));

    fs.writeFileSync(filename, [headers.join(','), ...rows].join('\n'), 'utf8');
    console.log(`\n📁 Saved to: ${filename}`);
    console.log(`✅ Done! ${finalPlayers.length} players scraped.`);
}

main().catch(err => {
    console.error('❌ Error:', err.message);
    process.exit(1);
});
