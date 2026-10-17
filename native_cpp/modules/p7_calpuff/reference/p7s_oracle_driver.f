c-----------------------------------------------------------------------
      program p7s_oracle
c-----------------------------------------------------------------------
c
c --- CTEAS P7S FORTRAN ORACLE DRIVER -- hand written for this test
c     harness. This file is NOT vendor source and is never used by the
c     model; it drives the UNMODIFIED vendor units extracted by
c     reference/p7s_source_anchor.py: TERAVG, TRELIEF and GETELEV.
c
c --- The elevation grid is supplied per case into /METHD/; GETCELL (which
c     GETELEV uses only to resolve the domain) is a stub that returns the
c     single domain 1, mirrored by the C++ test.
c
c --- Input on stdin, list directed:
c     line 1: mode
c     mode 1: icase nx ny i0 j0 i j   then nx*ny elevations   -> elavg
c     mode 2: icase nx ny             then nx*ny elevations   -> 5*nx*ny relief values
c     mode 3: icase nx ny x y         then nx*ny elevations   -> z
c     (the elevation grid is a separate record so that the list-directed
c      header read does not swallow it)
c-----------------------------------------------------------------------
      include 'params.puf'
      include 'methd.puf'
      include 'gridnest.puf'
      include 'grid.puf'
c
      integer mode,ios,icase,nx_i,ny_i,i0_i,j0_i,i_i,j_i,ii,jj,kk
      real el(400),elavg_o,z_o,x_i,y_i
      real relief_o(2000)
c
      read(*,*,iostat=ios) mode
      if(ios.ne.0) stop 'P7S oracle: missing mode'
c
      if(mode.eq.1)then
 10      read(*,*,iostat=ios) icase,nx_i,ny_i,i0_i,j0_i,i_i,j_i
         if(ios.ne.0) goto 999
         call p7s_setgrid(nx_i,ny_i,el)
         call teravg(.FALSE.,i0_i,j0_i,i_i,j_i,1,elavg_o)
         write(*,'(i8,1x,es20.12)') icase,elavg_o
         goto 10
      endif
c
      if(mode.eq.2)then
 20      read(*,*,iostat=ios) icase,nx_i,ny_i
         if(ios.ne.0) goto 999
         call p7s_setgrid(nx_i,ny_i,el)
         call trelief(.FALSE.)
         kk=0
         do jj=1,ny_i
         do ii=1,nx_i
            kk=kk+1
            relief_o(kk)=relief(1,ii,jj,1)
         enddo
         enddo
         do jj=1,ny_i
         do ii=1,nx_i
            kk=kk+1
            relief_o(kk)=relief(2,ii,jj,1)
         enddo
         enddo
         do jj=1,ny_i
         do ii=1,nx_i
            kk=kk+1
            relief_o(kk)=relief(3,ii,jj,1)
         enddo
         enddo
         do jj=1,ny_i
         do ii=1,nx_i
            kk=kk+1
            relief_o(kk)=relief(4,ii,jj,1)
         enddo
         enddo
         do jj=1,ny_i
         do ii=1,nx_i
            kk=kk+1
            relief_o(kk)=relief(5,ii,jj,1)
         enddo
         enddo
         write(*,'(i8,2000(1x,es20.12))') icase,(relief_o(kk),kk=1,
     &      5*nx_i*ny_i)
         goto 20
      endif
c
 30   continue
      read(*,*,iostat=ios) icase,nx_i,ny_i,x_i,y_i
      if(ios.ne.0) goto 999
      call p7s_setgrid(nx_i,ny_i,el)
      call getelev(x_i,y_i,z_o)
      write(*,'(i8,1x,es20.12)') icase,z_o
      goto 30
c
 999  continue
      end
c-----------------------------------------------------------------------
      subroutine p7s_setgrid(nx_i,ny_i,el)
c-----------------------------------------------------------------------
c --- Read the case's elevation grid into /METHD/ (i fastest) and set the
c     grid sizes. The values come from the case line, one per cell.
      include 'params.puf'
      include 'methd.puf'
      include 'gridnest.puf'
      integer nx_i,ny_i,ii,jj,kk,ios2,nn
      real el(400)
      read(*,*,iostat=ios2) (el(nn),nn=1,nx_i*ny_i)
      if(ios2.ne.0) stop 'P7S oracle: missing elevation grid'
      kk=0
      do jj=1,ny_i
      do ii=1,nx_i
         kk=kk+1
         elev(ii,jj,1)=el(kk)
      enddo
      enddo
      nxm(1)=nx_i
      nym(1)=ny_i
      ngrid=1
c --- Single non-nested domain: the vendor's SETUP sets these to 1 and 0.
      nestfac(1)=1.0
      rnxnest0(1)=0.0
      rnynest0(1)=0.0
      return
      end
c-----------------------------------------------------------------------
      subroutine getcell(acall,axy,idom,x,y,dx,dy,icell,jcell,kdom)
c-----------------------------------------------------------------------
c --- Domain stub: the oracle uses the single domain 1.
      character*12 acall,axy
      integer idom,icell,jcell,kdom
      real x,y,dx,dy
      icell=1
      jcell=1
      kdom=1
      return
      end
