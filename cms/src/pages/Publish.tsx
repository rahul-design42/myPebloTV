import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/client';
import { AlertTriangle, CheckCircle } from 'lucide-react';

export default function Publish() {
  const queryClient = useQueryClient();

  const { data: report, isLoading: loadingReport } = useQuery({
    queryKey: ['validation-report'],
    queryFn: () => api.getValidationReport(),
  });

  const { data: runs, isLoading: loadingRuns } = useQuery({
    queryKey: ['publish-runs'],
    queryFn: () => api.getPublishRuns(),
  });

  const publishMutation = useMutation({
    mutationFn: () => api.publishCatalog(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['publish-runs'] });
      alert('Catalogue published successfully!');
    },
    onError: (err: any) => {
      alert(`Publish failed: ${err.message}`);
    }
  });

  const isBlocked = report?.blocking_issues?.length > 0;

  return (
    <div>
      <h2>Publish Catalogue</h2>
      <p style={{ color: 'var(--text-muted)', marginBottom: '2rem' }}>
        Review content validation issues before generating the static JSON catalogue.
      </p>

      {loadingReport ? (
        <div>Loading validation report...</div>
      ) : (
        <div className="card" style={{ marginBottom: '2rem' }}>
          <div className="header-flex" style={{ marginBottom: '1rem' }}>
            <h3 style={{ margin: 0 }}>Validation Report</h3>
            <button 
              className={`btn ${isBlocked ? 'btn-secondary' : ''}`}
              onClick={() => publishMutation.mutate()}
              disabled={isBlocked || publishMutation.isPending}
            >
              {publishMutation.isPending ? 'Publishing...' : 'Publish Now'}
            </button>
          </div>

          {isBlocked && (
            <div style={{ background: '#fef2f2', border: '1px solid #fca5a5', padding: '1rem', borderRadius: '4px', marginBottom: '1.5rem', display: 'flex', alignItems: 'flex-start', gap: '0.75rem' }}>
              <AlertTriangle color="var(--danger)" />
              <div>
                <strong style={{ color: '#991b1b', display: 'block' }}>Cannot Publish</strong>
                <span style={{ color: '#b91c1c' }}>There are {report.blocking_issues.length} blocking issues that must be resolved.</span>
              </div>
            </div>
          )}

          {!isBlocked && (
            <div style={{ background: '#ecfdf5', border: '1px solid #6ee7b7', padding: '1rem', borderRadius: '4px', marginBottom: '1.5rem', display: 'flex', alignItems: 'flex-start', gap: '0.75rem' }}>
              <CheckCircle color="var(--success)" />
              <div>
                <strong style={{ color: '#065f46', display: 'block' }}>Ready to Publish</strong>
                <span style={{ color: '#047857' }}>All mandatory requirements are met.</span>
              </div>
            </div>
          )}

          {report?.blocking_issues?.length > 0 && (
            <div style={{ marginBottom: '1.5rem' }}>
              <h4 style={{ color: 'var(--danger)', marginBottom: '0.5rem' }}>Blocking Issues</h4>
              <ul style={{ paddingLeft: '1.5rem' }}>
                {report.blocking_issues.map((issue: any) => (
                  <li key={issue.id} style={{ marginBottom: '0.5rem' }}>
                    <strong>[{issue.entity_type} {issue.entity_id}]</strong> {issue.issue_type}: {issue.description}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {report?.non_blocking_issues?.length > 0 && (
            <div>
              <h4 style={{ color: '#d97706', marginBottom: '0.5rem' }}>Non-Blocking Warnings</h4>
              <ul style={{ paddingLeft: '1.5rem' }}>
                {report.non_blocking_issues.map((issue: any) => (
                  <li key={issue.id} style={{ marginBottom: '0.5rem' }}>
                    <strong>[{issue.entity_type} {issue.entity_id}]</strong> {issue.issue_type}: {issue.description}
                  </li>
                ))}
              </ul>
            </div>
          )}
          
          {report?.blocking_issues?.length === 0 && report?.non_blocking_issues?.length === 0 && (
            <p>No issues found.</p>
          )}
        </div>
      )}

      {loadingRuns ? (
        <div>Loading history...</div>
      ) : (
        <div className="card">
          <h3 style={{ marginBottom: '1rem' }}>Publish History</h3>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
            <thead>
              <tr style={{ background: 'var(--bg)', borderBottom: '1px solid var(--border)' }}>
                <th style={{ padding: '0.75rem' }}>Date</th>
                <th style={{ padding: '0.75rem' }}>Status</th>
                <th style={{ padding: '0.75rem' }}>Shows</th>
                <th style={{ padding: '0.75rem' }}>Episodes</th>
              </tr>
            </thead>
            <tbody>
              {runs?.runs?.map((run: any) => (
                <tr key={run.id} style={{ borderBottom: '1px solid var(--border)' }}>
                  <td style={{ padding: '0.75rem' }}>{new Date(run.started_at).toLocaleString()}</td>
                  <td style={{ padding: '0.75rem' }}>
                    {run.status === 'success' ? (
                      <span style={{ color: 'var(--success)', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                        <CheckCircle size={14} /> Success
                      </span>
                    ) : (
                      <span style={{ color: 'var(--danger)', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                        <AlertTriangle size={14} /> {run.status}
                      </span>
                    )}
                  </td>
                  <td style={{ padding: '0.75rem' }}>{run.shows_published || 0}</td>
                  <td style={{ padding: '0.75rem' }}>{run.episodes_published || 0}</td>
                </tr>
              ))}
              {(!runs?.runs || runs.runs.length === 0) && (
                <tr>
                  <td colSpan={4} style={{ padding: '1rem', textAlign: 'center', color: 'var(--text-muted)' }}>
                    No publish runs found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
