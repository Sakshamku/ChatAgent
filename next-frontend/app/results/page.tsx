"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { getTestResults, TestResult, deleteTestResult } from "@/lib/api";
import {
  Container,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Button,
  Box,
  Typography,
  CircularProgress,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from "@mui/material";
import DeleteIcon from "@mui/icons-material/Delete";
import VisibilityIcon from "@mui/icons-material/Visibility";

function safeNumber(value: number | null | undefined, fallback = 0) {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

function formatNumber(value: number | null | undefined, digits = 1) {
  return safeNumber(value).toFixed(digits);
}

export default function ResultsPage() {
  const { token, user, loading: authLoading } = useAuth();
  const router = useRouter();
  const [results, setResults] = useState<TestResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [selectedResultId, setSelectedResultId] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    if (authLoading) return;
    if (!token || !user) {
      setLoading(false);
      router.replace("/login");
      return;
    }

    const fetchResults = async () => {
      try {
        setLoading(true);
        const data = await getTestResults(token);
        setResults(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load results");
      } finally {
        setLoading(false);
      }
    };

    fetchResults();
  }, [authLoading, token, user, router]);

  const handleDeleteClick = (resultId: string) => {
    setSelectedResultId(resultId);
    setDeleteConfirmOpen(true);
  };

  const handleDeleteConfirm = async () => {
    if (!token || !selectedResultId) return;

    try {
      setDeleting(true);
      await deleteTestResult(selectedResultId, token);
      setResults(results.filter((r) => r.id !== selectedResultId));
      setDeleteConfirmOpen(false);
      setSelectedResultId(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete result");
    } finally {
      setDeleting(false);
    }
  };

  const handleDeleteCancel = () => {
    setDeleteConfirmOpen(false);
    setSelectedResultId(null);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("en-IN", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const formatTime = (seconds: number) => {
    const safeSeconds = safeNumber(seconds);
    const mins = Math.floor(safeSeconds / 60);
    const secs = safeSeconds % 60;
    return `${mins}m ${secs}s`;
  };

  if (loading) {
    return (
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "60vh" }}>
          <CircularProgress />
        </Box>
      </Container>
    );
  }

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Typography variant="h4" component="h1" gutterBottom sx={{ mb: 3, fontWeight: 600 }}>
        Test Results
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {results.length === 0 ? (
        <Paper sx={{ p: 3, textAlign: "center" }}>
          <Typography color="textSecondary">No test results yet. Take a test to see results here.</Typography>
        </Paper>
      ) : (
        <TableContainer component={Paper}>
          <Table>
            <TableHead sx={{ backgroundColor: "#f5f5f5" }}>
              <TableRow>
                <TableCell sx={{ fontWeight: 600 }}>Test Name</TableCell>
                <TableCell align="right" sx={{ fontWeight: 600 }}>
                  Score
                </TableCell>
                <TableCell align="right" sx={{ fontWeight: 600 }}>
                  Accuracy
                </TableCell>
                <TableCell align="right" sx={{ fontWeight: 600 }}>
                  Time
                </TableCell>
                <TableCell sx={{ fontWeight: 600 }}>Date</TableCell>
                <TableCell align="center" sx={{ fontWeight: 600 }}>
                  Actions
                </TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {results.map((result) => (
                <TableRow key={result.id} hover>
                  <TableCell>{result.test_name}</TableCell>
                  <TableCell align="right">
                    <span style={{ fontWeight: 600 }}>
                      {result.correct_answers}/{result.total_questions}
                    </span>
                  </TableCell>
                  <TableCell align="right">
                    <span style={{ fontWeight: 600, color: safeNumber(result.percentage) >= 70 ? "#4caf50" : "#ff9800" }}>
                      {formatNumber(result.percentage)}%
                    </span>
                  </TableCell>
                  <TableCell align="right">{formatTime(result.time_taken_seconds)}</TableCell>
                  <TableCell>{formatDate(result.attempted_at)}</TableCell>
                  <TableCell align="center">
                    <Box sx={{ display: "flex", gap: 1, justifyContent: "center" }}>
                      <Link href={`/results/${result.id}`}>
                        <Button size="small" variant="outlined" startIcon={<VisibilityIcon />}>
                          View
                        </Button>
                      </Link>
                      <Button
                        size="small"
                        variant="outlined"
                        color="error"
                        startIcon={<DeleteIcon />}
                        onClick={() => handleDeleteClick(result.id)}
                      >
                        Delete
                      </Button>
                    </Box>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      <Dialog open={deleteConfirmOpen} onClose={handleDeleteCancel}>
        <DialogTitle>Delete Test Result?</DialogTitle>
        <DialogContent>
          <Typography>Are you sure you want to delete this test result? This action cannot be undone.</Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleDeleteCancel}>Cancel</Button>
          <Button onClick={handleDeleteConfirm} color="error" variant="contained" disabled={deleting}>
            {deleting ? "Deleting..." : "Delete"}
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
}
