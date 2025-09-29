// netlify/functions/api.js
const BACKEND_URL = 'https://lab-app-donnees-opurbaines.onrender.com';

exports.handler = async (event, context) => {
    console.log('📍 Fonction Netlify appelée:', event.path, event.httpMethod);
    console.log('📋 Query parameters:', event.queryStringParameters);
    
    const headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS'
    };

    // CORS preflight
    if (event.httpMethod === 'OPTIONS') {
        return { statusCode: 200, headers, body: '' };
    }

    try {
        // Construire l'URL pour le backend Render
        const path = event.path.replace('/.netlify/functions/api', '/api');
        const queryString = event.rawQuery ? `?${event.rawQuery}` : '';
        const backendUrl = `${BACKEND_URL}${path}${queryString}`;
        
        console.log('🔗 Appel backend:', backendUrl);

        const renderResponse = await fetch(backendUrl, {
            method: event.httpMethod,
            headers: {
                'Content-Type': 'application/json',
            },
            // Timeout de 10 secondes
            signal: AbortSignal.timeout(10000)
        });

        console.log('📡 Statut backend:', renderResponse.status);

        if (renderResponse.ok) {
            const data = await renderResponse.json();
            console.log('✅ Backend Render fonctionne');
            return {
                statusCode: 200,
                headers,
                body: JSON.stringify(data)
            };
        } else {
            console.log('❌ Erreur backend:', renderResponse.status);
            // Si le backend renvoie une erreur, utiliser les données de secours
            return getFallbackData(event, headers);
        }
    } catch (error) {
        console.log('🔴 Erreur fetch:', error.message);
        console.log('🔄 Utilisation des données de secours');
        
        // Utiliser les données de secours en cas d'erreur
        return getFallbackData(event, headers);
    }
};

function getFallbackData(event, headers) {
    const path = event.path.replace('/.netlify/functions/api', '');
    
    console.log('🎯 Route de secours:', path);

    // Routes de secours
    if (path === '/villes' || path === '/villes/') {
        return {
            statusCode: 200,
            headers,
            body: JSON.stringify(['Douala', 'Yaoundé'])
        };
    }

    if (path === '/communes' || path === '/communes/') {
        const ville = event.queryStringParameters?.ville || '';
        console.log('🏙️ Ville demandée:', ville);
        
        let communes = [];
        
        if (ville.toLowerCase().includes('douala')) {
            communes = ['Douala I', 'Douala II', 'Douala III', 'Douala IV', 'Douala V'];
        } else if (ville.toLowerCase().includes('yaound')) {
            communes = ['Yaoundé I', 'Yaoundé II', 'Yaoundé III', 'Yaoundé IV', 'Yaoundé V', 'Yaoundé VI', 'Yaoundé VII'];
        }
        
        console.log('🏘️ Communes retournées:', communes);
        
        return {
            statusCode: 200,
            headers,
            body: JSON.stringify(communes)
        };
    }

    if (path === '/indicateurs' || path === '/indicateurs/') {
        const commune = event.queryStringParameters?.commune || '';
        console.log('📊 Indicateurs pour commune:', commune);
        
        return {
            statusCode: 200,
            headers,
            body: JSON.stringify({
                commune: commune,
                ville: commune.includes('Douala') ? 'Douala' : 'Yaoundé',
                stats_generales: {
                    nombre_troncons: 12,
                    total_lineaire_ml: 15000,
                    total_superficie_taudis: 45000,
                    moyenne_points_lumineux: 35
                },
                troncons_voirie: [
                    {
                        quartier: "Quartier A",
                        nom: "Boulevard Principal",
                        lineaire_ml: 2500,
                        classe: "Primaire",
                        nid_poule: "Oui",
                        points_lumineux: 45,
                        image: "troncon1.jpg"
                    },
                    {
                        quartier: "Quartier B", 
                        nom: "Rue Secondaire",
                        lineaire_ml: 1800,
                        classe: "Secondaire",
                        nid_poule: "Non",
                        points_lumineux: 28,
                        image: "troncon2.jpg"
                    }
                ],
                quartiers_taudis: [
                    {
                        nom: "Quartier B",
                        superficie_m2: 12500,
                        image: "taudis1.jpg"
                    },
                    {
                        nom: "Quartier C",
                        superficie_m2: 8500,
                        image: "taudis2.jpg"
                    }
                ],
                analyse_classes_voirie: {
                    "Primaire": 8,
                    "Secondaire": 4
                },
                analyse_nids_poule: {
                    "Oui": 7,
                    "Non": 5
                }
            })
        };
    }

    if (path === '/health' || path === '/health/') {
        return {
            statusCode: 200,
            headers,
            body: JSON.stringify({
                status: 'healthy',
                message: 'Netlify Function active',
                backend: 'fallback',
                timestamp: new Date().toISOString()
            })
        };
    }

    return {
        statusCode: 404,
        headers,
        body: JSON.stringify({ 
            error: 'Route non trouvée',
            path: path,
            available_routes: ['/villes', '/communes', '/indicateurs', '/health']
        })
    };
}