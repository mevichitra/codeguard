// MUST trigger CG-SEC-104
export const Comment = ({ dirty }: { dirty: string }) => (
  <div dangerouslySetInnerHTML={{ __html: dirty }} />
);
