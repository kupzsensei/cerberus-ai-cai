import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { getLocalStorageJobStatus } from '../../api/apiService';
import MarkdownRenderer from '../../components/MarkdownRenderer';

export default function LocalStorageResultPage() {
    const { jobId } = useParams();
    const [job, setJob] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchStatus = async () => {
            const jobStatus = await getLocalStorageJobStatus(jobId);
            setJob(jobStatus);
            if (jobStatus.status === 'completed' || jobStatus.status === 'failed') {
                setLoading(false);
            } else {
                setTimeout(fetchStatus, 2000);
            }
        };
        fetchStatus();
    }, [jobId]);

    return (
        <div className="w-full h-full flex flex-col p-5 bg-gray-900 text-white">
            <h1 className="text-2xl font-bold mb-5">Query Result</h1>
            {loading && <p>Processing...</p>}
            {job && (
                <div>
                    <p><strong>Job ID:</strong> {job.job_id}</p>
                    <p><strong>Status:</strong> {job.status}</p>
                    <p><strong>Prompt:</strong> {job.prompt}</p>
                    <p><strong>Files:</strong> {job.filenames.join(', ')}</p>
                    {job.result && (
                        <div className="mt-5">
                            <h2 className="text-xl font-bold">Result:</h2>
                            <MarkdownRenderer content={job.result.processed_text} />
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}