const API = {
    async request(path, method = 'GET', body = null) {
        const userId = localStorage.getItem('user_id');
        const options = {
            method,
            headers: { 'Content-Type': 'application/json' }
        };
        if (userId) options.headers['X-User-Id'] = userId;
        if (body) options.body = JSON.stringify(body);

        const resp = await fetch(path, options);
        const text = await resp.text();
        
        try {
            const data = JSON.parse(text);
            // Handle cases where status might be missing from server (just in case)
            if (!data.status && resp.ok) data.status = 'ok';
            if (!data.status && !resp.ok) data.status = 'error';
            return data;
        } catch (e) {
            console.error("API Error (Non-JSON):", text);
            return { status: 'error', message: text || "Unknown server error" };
        }
    }
};
