import { NextResponse } from 'next/server';
import { exec } from 'child_process';
import path from 'path';

export async function GET() {
  return new Promise((resolve) => {
    // Resolve path to the backend directory and run get_analytics.py
    const scriptPath = path.resolve(process.cwd(), '../backend/src/get_analytics.py');

    // Run the script using 'uv run python' to leverage the project's venv
    exec(
      `uv run python "${scriptPath}"`,
      { cwd: path.resolve(process.cwd(), '../backend') },
      (error, stdout, stderr) => {
        if (error) {
          console.error('Failed to run analytics script:', error, stderr);
          return resolve(
            NextResponse.json({ error: 'Failed to fetch analytics' }, { status: 500 })
          );
        }
        try {
          const data = JSON.parse(stdout);
          return resolve(NextResponse.json(data));
        } catch (parseError) {
          console.error('Failed to parse script output:', parseError, stdout);
          return resolve(NextResponse.json({ error: 'Invalid analytics output' }, { status: 500 }));
        }
      }
    );
  });
}
