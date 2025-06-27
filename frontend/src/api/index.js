export const API_BASE_URL = 'http://127.0.0.1:8000'
export const OLLAMA_BASE_URL = 'http://10.254.10.25:11434'


export const getOllamaModelsAPI = async () => {
    const response = await fetch(`${OLLAMA_BASE_URL}/api/tags`)

    const res = await response.json()
    // console.log( res.models)
    return await res.models
}