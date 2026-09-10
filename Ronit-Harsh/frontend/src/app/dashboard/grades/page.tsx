"use client"

import { useEffect, useState } from "react"
import { useAuth } from "@/context/AuthContext"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card"
import { Button } from "@/components/ui/Button"
import { Loader2, TrendingUp, BookOpen, GraduationCap, ArrowUpRight } from "lucide-react"
import { AimsConnectModal } from "@/components/aims/AimsConnectModal"
import { API_URL } from "@/lib/utils"

export default function GradesPage() {
    const { session, user } = useAuth()
    const [loading, setLoading] = useState(true)
    const [data, setData] = useState<any>(null)
    const [isAimsModalOpen, setIsAimsModalOpen] = useState(false)

    useEffect(() => {
        document.title = "Grades - Student Helper"
    }, [])

    useEffect(() => {
        if (session) {
            fetchGrades()
        }
    }, [session])

    const fetchGrades = async () => {
        try {
            setLoading(true)
            const res = await fetch(`${API_URL}/aims/data`, {
                headers: {
                    "Authorization": `Bearer ${session?.access_token}`
                }
            })
            if (res.ok) {
                const json = await res.json()
                setData(json)
            }
        } catch (e) {
            console.error("Failed to fetch grades", e)
        } finally {
            setLoading(false)
        }
    }

    if (loading && !data) {
        return (
            <div className="flex h-full items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-purple-500" />
            </div>
        )
    }

    // Process Data
    const gpaHistory = data?.gpa || []
    const currentGPA = gpaHistory.length > 0 ? gpaHistory[0] : null
    const grades = data?.grades || []

    // Group Grades by Semester
    const gradesBySemester = grades.reduce((acc: any, grade: any) => {
        if (!acc[grade.semester]) {
            acc[grade.semester] = []
        }
        acc[grade.semester].push(grade)
        return acc
    }, {})

    // Helper to parse "JAN26-APR26" -> value for sorting
    const parseSemester = (sem: string) => {
        try {
            // format: MMMYY-MMMYY
            // We only need the first part
            const start = sem.split("-")[0] // JAN26
            const monthStr = start.slice(0, 3)
            const yearStr = start.slice(3)

            const months: { [key: string]: number } = {
                "JAN": 0, "FEB": 1, "MAR": 2, "APR": 3, "MAY": 4, "JUN": 5,
                "JUL": 6, "AUG": 7, "SEP": 8, "OCT": 9, "NOV": 10, "DEC": 11
            }

            const year = parseInt(yearStr) + 2000 // Assume 20xx
            const month = months[monthStr.toUpperCase()] || 0

            return year * 12 + month
        } catch (e) {
            return 0
        }
    }

    const uniqueSemesters: string[] = Array.from(new Set(grades.map((g: any) => g.semester)))

    // Sort Chronologically (Oldest First) to assign IDs
    const sortedSemesters = uniqueSemesters.sort((a, b) => parseSemester(a) - parseSemester(b))

    // Create Map for Display Names (Semester 1, Semester 2...)
    const semesterLabels: { [key: string]: string } = {}
    sortedSemesters.forEach((sem, index) => {
        semesterLabels[sem] = `Semester ${index + 1}`
    })

    // For Display: Reverse Chronological (Newest First)
    const displaySemesters = [...sortedSemesters].reverse()

    const getGradeColor = (grade: string) => {
        if (!grade) return "text-slate-400"
        if (grade.startsWith("A")) return "text-green-500"
        if (grade.startsWith("B")) return "text-yellow-500"
        if (grade.startsWith("C")) return "text-orange-500"
        if (grade.startsWith("F")) return "text-red-500"
        return "text-blue-500"
    }

    return (
        <div className="space-y-8">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-3xl font-bold">Academic Performance</h2>
                    <p className="text-slate-400 mt-1">Track your grades, GPA, and course history.</p>
                </div>
                <Button
                    onClick={() => setIsAimsModalOpen(true)}
                    className="bg-purple-600 hover:bg-purple-700"
                >
                    <ArrowUpRight className="mr-2 h-4 w-4" />
                    Sync AIMS Data
                </Button>
            </div>

            {/* GPA Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-stretch">
                <Card className="relative overflow-hidden bg-slate-900/50 border-slate-800 backdrop-blur-sm h-full flex flex-col justify-between">
                    <div className="absolute top-0 right-0 p-4 opacity-10">
                        <TrendingUp className="h-24 w-24 text-purple-500" />
                    </div>
                    <div>
                        <CardHeader className="pb-2">
                            <CardTitle className="text-sm font-medium text-slate-400">Cumulative GPA</CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="flex items-baseline gap-2">
                                <div className="text-5xl font-bold text-white tracking-tight">
                                    {currentGPA?.cgpa?.toFixed(2) || "N/A"}
                                </div>
                                <span className="text-sm text-slate-500 font-medium">/ 10.0</span>
                            </div>
                        </CardContent>
                    </div>
                    <CardContent className="pt-0 pb-6">
                        <div className="flex items-center gap-2">
                            <div className="h-1.5 flex-1 bg-slate-800 rounded-full overflow-hidden">
                                <div
                                    className="h-full bg-gradient-to-r from-purple-500 to-pink-500 rounded-full"
                                    style={{ width: `${(currentGPA?.cgpa || 0) * 10}%` }}
                                />
                            </div>
                        </div>
                    </CardContent>
                </Card>

                <Card className="bg-slate-900 border-slate-800 flex flex-col h-full">
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
                        <CardTitle className="text-sm font-medium text-slate-400">SGPA History</CardTitle>
                        <BookOpen className="h-4 w-4 text-blue-500" />
                    </CardHeader>
                    <CardContent className="flex-1">
                        {gpaHistory && gpaHistory.length > 0 ? (
                            <div className={`grid ${gpaHistory.length >= 4 ? 'grid-cols-2 gap-x-12 gap-y-2' : 'grid-cols-1 gap-y-3'}`}>
                                {gpaHistory.map((gpa: any) => (
                                    gpa.sgpa ? (
                                        <div key={gpa.semester} className="flex items-center justify-between text-sm group hover:bg-slate-800/50 p-2 rounded-md transition-colors -mx-2 bg-transparent">
                                            <div className="flex items-center gap-3">
                                                <span className="text-white font-medium">{semesterLabels[gpa.semester]}</span>
                                            </div>
                                            <span className={`font-bold ${gpa.sgpa >= 9 ? 'text-green-400' : 'text-white'}`}>{gpa.sgpa.toFixed(2)}</span>
                                        </div>
                                    ) : null
                                ))}
                            </div>
                        ) : (
                            <div className="text-4xl font-bold text-white">N/A</div>
                        )}
                        {(!gpaHistory || gpaHistory.length === 0) && (
                            <p className="text-xs text-slate-500 mt-1">
                                Last Semester
                            </p>
                        )}
                    </CardContent>
                </Card>

                <Card className="relative overflow-hidden bg-slate-900/50 border-slate-800 backdrop-blur-sm h-full flex flex-col justify-between">
                    <div className="absolute top-0 right-0 p-4 opacity-10">
                        <GraduationCap className="h-24 w-24 text-blue-500" />
                    </div>
                    <div>
                        <CardHeader className="pb-2">
                            <CardTitle className="text-sm font-medium text-slate-400">Total Credits</CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="flex items-baseline gap-2">
                                <div className="text-5xl font-bold text-white tracking-tight">
                                    {grades.reduce((sum: number, g: any) => {
                                        if (g.course_code === "CI101" || g.course_type === "Additional" || g.course_type === "Audit") return sum
                                        return sum + (g.grade ? g.credits : 0)
                                    }, 0)}
                                </div>
                                <span className="text-sm text-slate-500">Credits</span>
                            </div>
                        </CardContent>
                    </div>
                    <CardContent className="pt-0 pb-6">
                        <p className="text-xs text-slate-400">
                            Completed core & elective credits (excluding additional/audit)
                        </p>
                    </CardContent>
                </Card>
            </div>

            {/* Empty State */}
            {uniqueSemesters.length === 0 && !loading && (
                <div className="text-center py-20 border border-dashed border-slate-800 rounded-lg">
                    <GraduationCap className="h-10 w-10 text-slate-600 mx-auto mb-4" />
                    <h3 className="text-lg font-medium text-white">No Grades Found</h3>
                    <p className="text-slate-400 mb-6">Connect your AIMS account to see your grades.</p>
                    <Button variant="outline" onClick={() => setIsAimsModalOpen(true)}>Connect AIMS</Button>
                </div>
            )}

            {/* Courses List */}
            <div className="space-y-8">
                {displaySemesters.map((semester: any) => {
                    const semesterCourses = gradesBySemester[semester] || []

                    // Filter out CI101 and Additional from main total
                    const mainCourses = semesterCourses.filter((c: any) =>
                        c.course_code !== "CI101" && c.course_type !== "Additional" && c.course_type !== "Audit"
                    )

                    const additionalCourses = semesterCourses.filter((c: any) =>
                        c.course_type === "Additional"
                    )

                    const totalCredits = mainCourses.reduce((sum: number, c: any) => sum + (c.grade ? c.credits : 0), 0)
                    const additionalCredits = additionalCourses.reduce((sum: number, c: any) => sum + (c.grade ? c.credits : 0), 0)

                    return (
                        <div key={semester} className="space-y-4">
                            <div className="flex items-center gap-4">
                                <h3 className="text-xl font-bold text-white">
                                    <span className="text-purple-400 mr-2">{semesterLabels[semester]}:</span>
                                    {semester}
                                </h3>

                                <span className="text-slate-500 text-sm font-medium">
                                    ({totalCredits} Credits{additionalCredits > 0 ? ` + ${additionalCredits} Additional` : ""})
                                </span>

                                <div className="h-px bg-slate-800 flex-1" />
                                {/* Find SGPA for this semester */}
                                {gpaHistory.find((g: any) => g.semester === semester)?.sgpa && (
                                    <span className="bg-green-500/10 text-green-500 px-3 py-1 rounded-full text-sm font-medium border border-green-500/20">
                                        SGPA: {gpaHistory.find((g: any) => g.semester === semester)?.sgpa}
                                    </span>
                                )}
                            </div>

                            <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
                                <table className="w-full text-left text-sm">
                                    <thead className="bg-slate-950 text-slate-400 font-medium border-b border-slate-800">
                                        <tr>
                                            <th className="px-6 py-4">Course Code</th>
                                            <th className="px-6 py-4">Course Name</th>
                                            <th className="px-6 py-4">Credits</th>
                                            <th className="px-6 py-4">Type</th>
                                            <th className="px-6 py-4 text-right">Grade</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-slate-800">
                                        {semesterCourses.map((course: any) => (
                                            <tr key={course.course_code} className="hover:bg-slate-800/50 transition-colors">
                                                <td className="px-6 py-4 font-mono text-slate-400">{course.course_code}</td>
                                                <td className="px-6 py-4 font-medium text-white">{course.course_name}</td>
                                                <td className="px-6 py-4 text-slate-400">{course.credits}</td>
                                                <td className="px-6 py-4 text-slate-500 truncate max-w-[200px]">{course.course_type}</td>
                                                <td className={`px-6 py-4 text-right font-bold ${getGradeColor(course.grade)}`}>
                                                    {course.grade || "-"}
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    )
                })}
            </div>

            <AimsConnectModal
                open={isAimsModalOpen}
                onOpenChange={setIsAimsModalOpen}
                onSuccess={fetchGrades}
            />
        </div>
    )
}
